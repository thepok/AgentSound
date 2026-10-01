// Tests for the click detector (engine/analysis/ClickDetector), the WAV reader (engine/io/WavReader),
// the waveform zoom and the analyser's image set (every report image written, valid PNG CRCs).
// Usage: test_clicks [outDir]  (images are written there; default: <temp>/agentsound_test_clicks).

#include "analysis/ClickDetector.h"
#include "analysis/MixAnalyzer.h"
#include "analysis/Png.h"
#include "analysis/WaveZoom.h"
#include "dsp/Dsp.h"
#include "instruments/DrumSynth.h"
#include "instruments/Dx7Banks.h"
#include "instruments/Dx7Synth.h"
#include "instruments/VaSynth.h"
#include "io/WavReader.h"
#include "io/WavWriter.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;
using as::json;
using as::analysis::ClickDetector;
using as::analysis::ClickEvent;
constexpr double kPi = 3.14159265358979323846;
constexpr double kSr = 48000.0;
int failures = 0;

void check(bool ok, const std::string& what) {
    std::printf("[%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
    if (!ok) ++failures;
}

std::string fmt(const char* f, double a, double b = 0.0, double c = 0.0) {
    char buf[256];
    std::snprintf(buf, sizeof buf, f, a, b, c);
    return buf;
}

struct Stereo {
    std::vector<float> L, R;
    std::size_t size() const { return L.size(); }
    void resize(std::size_t n) { L.assign(n, 0.0f); R.assign(n, 0.0f); }
    void add(const Stereo& o, double gain = 1.0) {
        for (std::size_t i = 0; i < std::min(size(), o.size()); ++i) {
            L[i] += static_cast<float>(gain * o.L[i]);
            R[i] += static_cast<float>(gain * o.R[i]);
        }
    }
};

Stereo sine(double seconds, double hz, double amp, double phase = 0.0) {
    Stereo s;
    s.resize(static_cast<std::size_t>(seconds * kSr));
    for (std::size_t i = 0; i < s.size(); ++i) {
        const auto v = static_cast<float>(amp * std::sin(2.0 * kPi * hz * static_cast<double>(i) / kSr + phase));
        s.L[i] = v;
        s.R[i] = v * 0.9f;
    }
    return s;
}

std::vector<ClickEvent> detect(const Stereo& s, int block = 256, ClickDetector::Settings set = {}) {
    ClickDetector det(kSr, set);
    for (std::size_t pos = 0; pos < s.size(); pos += static_cast<std::size_t>(block)) {
        const int n = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(block), s.size() - pos));
        det.feed(s.L.data() + pos, s.R.data() + pos, n);
    }
    det.finish();
    return det.events();
}

std::string listEvents(const std::vector<ClickEvent>& ev) {
    std::string s;
    for (std::size_t i = 0; i < ev.size() && i < 6; ++i)
        s += fmt(" [%.5f s, jump %.1f dB, contrast %.1f dB]", static_cast<double>(ev[i].sample) / kSr, ev[i].jumpDb(), ev[i].contrastDb());
    return s;
}

// ------------------------------------------------------------------ WAV reader

void writeBytes(const std::string& path, const std::string& bytes) {
    std::ofstream(path, std::ios::binary).write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
}
void put16(std::string& b, int v) { b.push_back(static_cast<char>(v & 0xff)); b.push_back(static_cast<char>((v >> 8) & 0xff)); }
void put32(std::string& b, std::uint32_t v) { for (int i = 0; i < 4; ++i) b.push_back(static_cast<char>((v >> (8 * i)) & 0xff)); }

void testWavReader(const std::string& dir) {
    const Stereo s = sine(0.25, 997.0, 0.7);
    for (int bits : {16, 24, 32}) {
        const std::string path = dir + "/rt_" + std::to_string(bits) + ".wav";
        {
            as::WavWriter w;
            w.open(path, 48000, bits, 7);
            w.write(s.L.data(), s.R.data(), static_cast<int>(s.size()));
        }
        const as::WavData d = as::readWav(path);
        double err = 0.0;
        for (std::size_t i = 0; i < s.size() && i < d.left.size(); ++i)
            err = std::max({err, std::fabs(static_cast<double>(d.left[i]) - s.L[i]), std::fabs(static_cast<double>(d.right[i]) - s.R[i])});
        const double lsb = bits == 16 ? 1.0 / 32768.0 : bits == 24 ? 1.0 / 8388608.0 : 0.0;
        check(d.sampleRate == 48000 && d.channels == 2 && d.bitsPerSample == bits && d.isFloat == (bits == 32) &&
                  d.totalFrames == static_cast<std::int64_t>(s.size()) && d.left.size() == s.size() && err <= 3.0 * lsb,
              fmt("WavReader round trip %.0f-bit: header ok, max error %.3g (<= 3 LSB: dither + writer scale 2^n-1)", bits, err));
        // Frame range, clipped at the end of the file.
        const as::WavData part = as::readWav(path, 1000, 64);
        const as::WavData tail = as::readWav(path, static_cast<std::int64_t>(s.size()) - 10, 100);
        bool same = part.left.size() == 64 && part.startFrame == 1000;
        for (std::size_t i = 0; same && i < 64; ++i) same = part.left[i] == d.left[1000 + i] && part.right[i] == d.right[1000 + i];
        check(same && tail.left.size() == 10, fmt("WavReader %.0f-bit: frame range and clipping at the end", bits));
    }
    {   // Hand-made mono 16-bit file with an extra chunk before 'data'.
        std::string b = "RIFF";
        put32(b, 0);
        b += "WAVEfmt ";
        put32(b, 16); put16(b, 1); put16(b, 1); put32(b, 44100); put32(b, 88200); put16(b, 2); put16(b, 16);
        b += "LIST"; put32(b, 3); b += "abc"; b.push_back(0);  // odd size + pad byte
        b += "data"; put32(b, 6); put16(b, 16384); put16(b, -32768); put16(b, 0);
        writeBytes(dir + "/mono16.wav", b);
        const as::WavData d = as::readWav(dir + "/mono16.wav");
        check(d.channels == 1 && d.sampleRate == 44100 && d.left.size() == 3 && d.left[0] == 0.5f && d.right[0] == 0.5f && d.left[1] == -1.0f,
              "WavReader: mono 16-bit (duplicated to L/R), odd-sized extra chunk skipped");
    }
    {   // WAVE_FORMAT_EXTENSIBLE, 24-bit, 3 channels (the first two are returned).
        std::string b = "RIFF";
        put32(b, 0);
        b += "WAVEfmt ";
        put32(b, 40); put16(b, 0xFFFE); put16(b, 3); put32(b, 48000); put32(b, 48000 * 9); put16(b, 9); put16(b, 24);
        put16(b, 22); put16(b, 24); put32(b, 7);
        put16(b, 1); b += std::string("\x00\x00\x00\x00\x10\x00\x80\x00\x00\xAA\x00\x38\x9B\x71", 14);  // KSDATAFORMAT_SUBTYPE_PCM
        b += "data"; put32(b, 9);
        for (int v : {0x400000, -0x400000, 0x100}) { b.push_back(static_cast<char>(v & 0xff)); b.push_back(static_cast<char>((v >> 8) & 0xff)); b.push_back(static_cast<char>((v >> 16) & 0xff)); }
        writeBytes(dir + "/ext24.wav", b);
        const as::WavData d = as::readWav(dir + "/ext24.wav");
        check(d.channels == 3 && d.left.size() == 1 && d.left[0] == 0.5f && d.right[0] == -0.5f, "WavReader: WAVE_FORMAT_EXTENSIBLE 24-bit, 3 channels");
    }
    bool threw = false;
    writeBytes(dir + "/bad.wav", std::string("RIFF\x04\x00\x00\x00WAVE", 12));
    try { (void)as::readWav(dir + "/bad.wav"); } catch (const std::runtime_error& e) { threw = std::string(e.what()).find("fmt") != std::string::npos; }
    bool threw2 = false;
    try { (void)as::readWavInfo(dir + "/does_not_exist.wav"); } catch (const std::runtime_error&) { threw2 = true; }
    check(threw && threw2, "WavReader: missing fmt chunk and missing file throw readable errors");
}

// ------------------------------------------------------------------ click detector: synthetic signals

void testTruePositives() {
    {   // Clean tones: nothing.
        Stereo s = sine(2.0, 440.0, 0.5);
        s.add(sine(2.0, 3520.0, 0.1));
        const auto ev = detect(s);
        check(ev.empty(), "clean 440 Hz + 3.5 kHz tones: no clicks" + listEvents(ev));
    }
    {   // A 1-sample step of 0.05 in a sine (the signal jumps by 0.05 and stays offset).
        Stereo s = sine(2.0, 440.0, 0.5);
        const std::size_t n0 = 52345;
        for (std::size_t i = n0; i < s.size(); ++i) { s.L[i] += 0.05f; s.R[i] += 0.05f; }
        const auto ev = detect(s);
        check(ev.size() == 1 && std::llabs(ev[0].sample - static_cast<long long>(n0)) <= 1 && std::fabs(ev[0].jump - 0.05f) < 0.01f,
              fmt("step of 0.05 in a -6 dBFS sine: exactly one click at sample %.0f (+-1), jump ~0.05", static_cast<double>(n0)) + listEvents(ev));
        check(!ev.empty() && ev[0].contrastDb() > 30.0 && ev[0].channels == 3, "the step sticks out > 30 dB and is found in both channels");
    }
    {   // A single-sample spike of 0.05 (a pop), left channel only.
        Stereo s = sine(2.0, 220.0, 0.4);
        const std::size_t n1 = 70001;
        s.L[n1] += 0.05f;
        const auto ev = detect(s);
        check(ev.size() == 1 && std::llabs(ev[0].sample - static_cast<long long>(n1)) <= 1 && ev[0].channels == 1,
              "single-sample spike of 0.05 in the left channel: one click, correct sample and channel" + listEvents(ev));
    }
    {   // A hard-cut note: 5 ms attack, then cut to silence mid-cycle.
        Stereo s;
        s.resize(static_cast<std::size_t>(2.0 * kSr));
        const std::size_t on = 24000, cut = 59259;
        for (std::size_t i = on; i < cut; ++i) {
            const double t = static_cast<double>(i - on) / kSr;
            const double v = 0.3 * std::min(1.0, t / 0.005) * std::sin(2.0 * kPi * 330.0 * t);
            s.L[i] = static_cast<float>(v);
            s.R[i] = static_cast<float>(v);
        }
        const auto ev = detect(s);
        check(ev.size() == 1 && std::llabs(ev[0].sample - static_cast<long long>(cut)) <= 1,
              fmt("hard-cut note (0.3 amplitude): one click at the cut, %.4f s", static_cast<double>(cut) / kSr) + listEvents(ev));
    }
    {   // Pop in silence and a click inside a quiet pad under a loud one: both found; block size does not matter.
        Stereo s = sine(1.5, 110.0, 0.02);
        s.L[30000] += 0.01f;
        s.R[30000] += 0.01f;
        const auto a = detect(s, 256), b = detect(s, 37);
        check(a.size() == 1 && b.size() == 1 && a[0].sample == b[0].sample && a[0].jump == b[0].jump,
              "small click (0.01) in a quiet tone: found, identical for 256- and 37-frame blocks" + listEvents(a));
    }
    {   // Below the floor: a 0.001 step (-60 dBFS) is ignored.
        Stereo s = sine(1.0, 440.0, 0.5);
        for (std::size_t i = 20000; i < s.size(); ++i) s.L[i] += 0.001f;
        check(detect(s).empty(), "a -60 dBFS step is below the audibility floor: ignored");
    }
}

// A synthetic drum loop: kicks starting at full level mid-cycle (a kink), a click layer, snares,
// 16th hats and claps, plus a pad and a band-limited saw bass. Nothing here is a defect.
Stereo syntheticLoop(double seconds, bool withPadAndBass) {
    Stereo s;
    s.resize(static_cast<std::size_t>(seconds * kSr));
    as::dsp::Rng rng(11);
    const double beat = 60.0 / 120.0;
    double hpState = 0.0, prevNoise = 0.0;
    for (std::size_t i = 0; i < s.size(); ++i) {
        const double t = static_cast<double>(i) / kSr;
        const double inBeat = std::fmod(t, beat), inSix = std::fmod(t, beat / 4.0);
        const int beatIdx = static_cast<int>(t / beat), sixIdx = static_cast<int>(t / (beat / 4.0));
        // Kick: instant attack, pitch sweep 200 -> 50 Hz, starts at phase 0 (odd beats: cos = full step).
        const double f = 50.0 + 150.0 * std::exp(-inBeat * 40.0);
        const double ph = 2.0 * kPi * (50.0 * inBeat + 150.0 / 40.0 * (1.0 - std::exp(-inBeat * 40.0)));
        (void)f;
        double v = 0.6 * std::exp(-inBeat * 6.0) * (beatIdx % 2 ? std::cos(ph) : std::sin(ph));
        // Click layer: 1 ms noise burst.
        const double noise = rng.bipolar();
        if (inBeat < 0.001) v += 0.15 * noise * (1.0 - inBeat / 0.001);
        // Snare on 2 and 4: tone + noise, instant attack.
        if (beatIdx % 2 == 1) v += std::exp(-inBeat * 20.0) * (0.25 * noise + 0.2 * std::sin(2.0 * kPi * 185.0 * inBeat));
        // Hats: 16th notes of high-passed noise.
        hpState = noise - prevNoise + 0.6 * hpState;
        prevNoise = noise;
        v += 0.12 * std::exp(-inSix * (sixIdx % 4 == 2 ? 20.0 : 70.0)) * hpState;
        double l = v, r = v;
        if (withPadAndBass) {
            double pad = 0.0, bass = 0.0;
            for (int k : {0, 4, 7}) pad += std::sin(2.0 * kPi * 220.0 * std::pow(2.0, k / 12.0) * t * 1.002);
            for (int h = 1; h <= 40; ++h) bass += std::sin(2.0 * kPi * 41.2 * h * t) / h;  // saw, E1
            l += 0.06 * pad + 0.15 * bass;
            r += 0.06 * pad * 0.9 + 0.15 * bass;
        }
        s.L[i] = static_cast<float>(l);
        s.R[i] = static_cast<float>(r * 0.97);
    }
    return s;
}

Stereo renderInstrument(as::Instrument& inst, const std::vector<std::pair<double, int>>& hits, double noteLen, double seconds,
                        float vel = 0.9f) {
    Stereo out;
    out.resize(static_cast<std::size_t>(seconds * kSr));
    struct Ev { std::size_t at; bool on; int id, pitch; };
    std::vector<Ev> ev;
    for (std::size_t k = 0; k < hits.size(); ++k) {
        ev.push_back({static_cast<std::size_t>(std::llround(hits[k].first * kSr)), true, static_cast<int>(k), hits[k].second});
        ev.push_back({static_cast<std::size_t>(std::llround((hits[k].first + noteLen) * kSr)), false, static_cast<int>(k), hits[k].second});
    }
    std::stable_sort(ev.begin(), ev.end(), [](const Ev& a, const Ev& b) { return a.at != b.at ? a.at < b.at : (!a.on && b.on); });
    std::size_t pos = 0, next = 0;
    while (pos < out.size()) {
        while (next < ev.size() && ev[next].at <= pos) {
            if (ev[next].on) inst.noteOn(ev[next].id, ev[next].pitch, vel);
            else inst.noteOff(ev[next].id);
            ++next;
        }
        std::size_t end = std::min(out.size(), pos + 256);
        if (next < ev.size()) end = std::min(end, ev[next].at);
        inst.process(out.L.data() + pos, out.R.data() + pos, static_cast<int>(end - pos));
        pos = end;
    }
    return out;
}

std::unique_ptr<as::Instrument> makeInst(std::unique_ptr<as::Instrument> inst, const json& params) {
    inst->configure(params);
    as::RenderContext ctx;
    ctx.sampleRate = kSr;
    ctx.seed = 3;
    inst->prepare(ctx);
    return inst;
}

std::vector<std::pair<double, int>> drumPattern(double seconds) {
    std::vector<std::pair<double, int>> hits;
    const double six = 60.0 / 120.0 / 4.0;
    for (int k = 0; k * six < seconds - 0.5; ++k) {
        if (k % 4 == 0) hits.push_back({k * six, 36});
        if (k % 8 == 4) hits.push_back({k * six, 38});
        if (k % 16 == 12) hits.push_back({k * six + 0.004, 39});
        hits.push_back({k * six, k % 4 == 2 ? 46 : 42});
        if (k % 16 == 15) hits.push_back({k * six, 45});
    }
    hits.push_back({0.0, 49});
    return hits;
}

void testNoFalsePositives() {
    {
        const Stereo loop = syntheticLoop(6.0, false);
        const auto ev = detect(loop);
        check(ev.empty(), "synthetic drum loop (instant kicks, click layer, snares, hats): no clicks" + listEvents(ev));
        const Stereo full = syntheticLoop(6.0, true);
        const auto ev2 = detect(full);
        check(ev2.empty(), "same loop with a pad and a band-limited 41 Hz saw bass: no clicks" + listEvents(ev2));
    }
    {   // The real drum machine, every kit.
        for (const char* kit : {"808", "909", "linn", "synthwave", "modern"}) {
            auto drums = makeInst(as::makeDrumSynth(), json{{"kit", kit}});
            const Stereo s = renderInstrument(*drums, drumPattern(8.0), 0.1, 8.0);
            ClickDetector det(kSr);
            det.feed(s.L.data(), s.R.data(), static_cast<int>(s.size()));
            det.finish();
            check(det.events().empty(), std::string("drums kit '") + kit + "': 8 s loop (kick, snare, clap, hats, tom, crash) without false clicks" +
                                            listEvents(det.events()));
            if (std::string(kit) == "synthwave")
                check(!det.onsets().empty(), "drum attacks are recognised as onsets (they explain spikes in a mix)");
        }
    }
    {   // DX7 basses: 16th-note arpeggios, every note starting on top of the previous one's tail. The
        // broadband energy barely rises at each attack, but the high-frequency content does (the
        // onsetHfRiseDb criterion); without it BASS 1 attacks read as clicks.
        std::string dxAssets;
        for (const char* candidate : {"assets", "../assets", "../../assets"})
            if (as::dx7BanksInstalled(candidate)) { dxAssets = candidate; break; }
        if (dxAssets.empty()) std::printf("SKIP: dx7 bass arpeggios (%s)\n", as::kDx7NoBanksHint);
        for (const char* voice : {"BASS 1", "SYN-BASS 1", "PLUCK BASS"}) {
            if (dxAssets.empty()) break;
            auto dx = as::makeDx7Synth();
            dx->configure(json{{"voice", voice}});
            as::RenderContext ctx;
            ctx.sampleRate = kSr;
            ctx.seed = 3;
            ctx.assetDir = dxAssets;
            dx->prepare(ctx);
            std::vector<std::pair<double, int>> notes;
            const int pattern[] = {33, 40, 45, 48, 52, 57, 52, 48, 45, 40, 36, 43, 48, 52, 55, 60};
            for (int k = 0; k < 48; ++k) notes.push_back({0.1 + k * 0.125, pattern[k % 16] - (k / 16) * 2});
            const Stereo s = renderInstrument(*dx, notes, 0.3, 6.8, 0.9f);
            const auto ev = detect(s);
            ClickDetector::Settings noHf;
            noHf.onsetHfRiseDb = 1000.0;
            const auto without = detect(s, 256, noHf);
            check(ev.empty(), std::string("dx7 '") + voice + "' 16th-note arpeggio: no clicks (" + std::to_string(without.size()) +
                                  " without the high-frequency onset test)" + listEvents(ev));
        }
    }
    {   // A saw bass with the default envelope, 8th notes: its periodic edges are not clicks.
        auto va = makeInst(as::makeVaSynth(), json{{"osc1.wave", "saw"}, {"cutoff", 3000}});
        std::vector<std::pair<double, int>> notes;
        for (int k = 0; k < 24; ++k) notes.push_back({0.1 + k * 0.25, k % 3 == 0 ? 28 : 40});
        const Stereo s = renderInstrument(*va, notes, 0.2, 7.0, 0.8f);
        const auto ev = detect(s);
        check(ev.empty(), "va saw bass (default envelope), 8th notes: no clicks" + listEvents(ev));
    }
}

void testRealClicks() {
    // A soft va voice (triangle) with a 1 ms release ends every note with an audible tick. (A bright
    // saw cut the same way is masked by its own edges, which are just as sharp.)
    auto va = makeInst(as::makeVaSynth(), json{{"osc1.wave", "triangle"}, {"amp.release", 0.001}, {"amp.attack", 0.003}, {"cutoff", 5000}});
    std::vector<std::pair<double, int>> notes;
    for (int k = 0; k < 6; ++k) notes.push_back({0.2 + k * 0.5, 45});
    const Stereo s = renderInstrument(*va, notes, 0.2, 3.5, 0.9f);
    const auto ev = detect(s);
    int atNoteEnds = 0;
    for (const auto& e : ev)
        for (const auto& n : notes)
            if (std::fabs(static_cast<double>(e.sample) / kSr - (n.first + 0.2)) < 0.003) ++atNoteEnds;
    check(atNoteEnds >= 4, fmt("va with amp.release 1 ms: the note ends are found as clicks (%.0f of 6)", atNoteEnds) + listEvents(ev));
}

// ------------------------------------------------------------------ analyser: report + images

bool validPng(const std::string& path, int& w, int& h) {
    try {
        const auto img = as::analysis::decodePng(as::analysis::readFileBytes(path));  // verifies every chunk CRC + Adler-32
        w = img.width;
        h = img.height;
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

json feed(as::MixAnalyzer& an, const Stereo& mix, const std::vector<Stereo>& nodes, const std::vector<std::string>& ids,
          std::vector<as::SectionMarker> sections, double bpm = 120.0) {
    an.prepare(kSr, bpm, std::move(sections), static_cast<double>(mix.size()) / kSr);
    std::vector<int> idx;
    for (const auto& id : ids) idx.push_back(an.addNode(id, id == "hall"));
    for (std::size_t pos = 0; pos < mix.size(); pos += 256) {
        const int n = static_cast<int>(std::min<std::size_t>(256, mix.size() - pos));
        for (std::size_t k = 0; k < nodes.size(); ++k) an.feedNode(idx[k], nodes[k].L.data() + pos, nodes[k].R.data() + pos, n);
        an.feedMix(mix.L.data() + pos, mix.R.data() + pos, n);
    }
    return an.finish();
}

void testAnalyzerClicksAndImages(const std::string& dir) {
    // Drums (real kit) + a pad + a "keys" part with one hard-cut note at 3.2104 s.
    const double seconds = 8.0;
    auto drums = makeInst(as::makeDrumSynth(), json{{"kit", "synthwave"}});
    Stereo dr = renderInstrument(*drums, drumPattern(seconds), 0.1, seconds);
    Stereo pad = sine(seconds, 220.0, 0.08);
    pad.add(sine(seconds, 277.2, 0.06));
    Stereo keys;
    keys.resize(dr.size());
    const std::size_t on = static_cast<std::size_t>(2.5 * kSr), cut = static_cast<std::size_t>(3.2104 * kSr);
    for (std::size_t i = on; i < cut; ++i) {
        const double t = static_cast<double>(i - on) / kSr;
        keys.L[i] = keys.R[i] = static_cast<float>(0.2 * std::min(1.0, t / 0.004) * std::sin(2.0 * kPi * 523.25 * t));
    }
    Stereo hall;  // a "bus" with a tail of the pad
    hall.resize(dr.size());
    for (std::size_t i = 2400; i < hall.size(); ++i) { hall.L[i] = 0.3f * pad.R[i - 2400]; hall.R[i] = 0.3f * pad.L[i - 2400]; }
    Stereo mix;
    mix.resize(dr.size());
    for (const Stereo* p : {&dr, &pad, &keys, &hall}) mix.add(*p);
    const std::string out = dir + "/song";
    fs::create_directories(out + "/clicks");
    writeBytes(out + "/spectrogram_07_stale.png", "x");  // from an older render: must be removed
    writeBytes(out + "/clicks/click_05.png", "x");
    as::MixAnalyzer an;
    const json r = feed(an, mix, {dr, pad, keys, hall}, {"drums", "pad", "keys", "hall"}, {{"intro", 0.0, 4.0}, {"drop", 4.0, seconds}});
    an.writeImages(out);
    std::ofstream(out + "/report.json") << as::formatReport(r);

    const json& clicks = r["clicks"];
    check(clicks.size() == 1, fmt("mix with one hard-cut note: exactly one click reported (got %.0f)", static_cast<double>(clicks.size())));
    if (!clicks.empty()) {
        const json& k = clicks[0];
        check(std::fabs(k["sec"].get<double>() - 3.2104) < 0.0005 && k["node"] == "keys" && k["inMix"] == true && k["severity"] == "high" &&
                  k["image"] == "clicks/click_01.png" && k["bar"] == 2 && std::fabs(k["beat"].get<double>() - 3.42) < 0.02,
              "the click: 3.2104 s = bar 2 beat 3.42, node 'keys', in the mix, high severity, image clicks/click_01.png | " + k.dump());
    }
    bool warned = false;
    for (const auto& w : r["warnings"]) warned = warned || (w["code"] == "clicks" && w["severity"] == "error");
    check(warned, "a 'clicks' error names the problem");
    check(r["global"]["clicks"] == 1 && r["summary"].get<std::string>().find("clicks 1") != std::string::npos, "summary and global count the click");

    // Every image listed in the report exists, decodes (CRC + Adler-32) and has the common width.
    std::vector<std::string> expected = {"overview.png", "loudness.png", "tracks.png", "bands.png", "stereo.png", "spectrogram.png",
                                         "spectrogram_01_intro.png", "spectrogram_02_drop.png", "clicks/click_01.png"};
    std::vector<std::string> listed;
    for (const auto& im : r["images"]) listed.push_back(im["file"].get<std::string>());
    check(listed == expected, "report.images lists overview, loudness, tracks, bands, stereo, spectrogram, 2 section zooms, 1 click");
    for (const auto& im : r["images"]) {
        int w = 0, h = 0;
        const std::string f = im["file"].get<std::string>();
        const bool ok = validPng(out + "/" + f, w, h);
        check(ok && w == 1600 && h >= 300 && h <= 1150 && im["shows"].get<std::string>().size() > 30,
              "image " + f + " written, valid PNG, " + std::to_string(w) + "x" + std::to_string(h));
    }
    check(!fs::exists(out + "/spectrogram_07_stale.png") && !fs::exists(out + "/clicks/click_05.png"),
          "stale section zooms / click images of an earlier render are removed");

    // The same without the cut: no clicks, no click images, no clicks folder content.
    Stereo clean;
    clean.resize(dr.size());
    for (const Stereo* p : {&dr, &pad, &hall}) clean.add(*p);
    as::MixAnalyzer an2;
    const json r2 = feed(an2, clean, {dr, pad, hall}, {"drums", "pad", "hall"}, {{"intro", 0.0, 4.0}, {"drop", 4.0, seconds}});
    check(r2["clicks"].empty(), "drums + pad + bus without defects: no clicks" + (r2["clicks"].empty() ? std::string() : " " + r2["clicks"].dump()));
    bool anyClickWarning = false;
    for (const auto& w : r2["warnings"]) anyClickWarning = anyClickWarning || w["code"] == "clicks";
    check(!anyClickWarning, "no 'clicks' warning for the clean mix");

    // A click that only one part has, hidden under a loud mix, is reported as masked (low severity).
    Stereo loud = clean;
    Stereo quiet = sine(seconds, 660.0, 0.0005);
    quiet.L[static_cast<std::size_t>(5.1 * kSr)] += 0.004f;
    loud.add(quiet);
    Stereo noise;
    noise.resize(dr.size());
    as::dsp::Rng rng(5);
    for (std::size_t i = 0; i < noise.size(); ++i) { noise.L[i] = 0.2f * rng.bipolar(); noise.R[i] = 0.2f * rng.bipolar(); }
    loud.add(noise);
    as::MixAnalyzer an3;
    const json r3 = feed(an3, loud, {dr, pad, hall, quiet, noise}, {"drums", "pad", "hall", "tick", "noise"}, {});
    bool masked = false;
    for (const auto& k : r3["clicks"]) masked = masked || (k["node"] == "tick" && k["inMix"] == false && k["severity"] == "low");
    check(masked, "a click hidden under loud noise is reported for its part as masked (inMix false, low)");
}

void testZoomImage(const std::string& dir) {
    as::analysis::WaveZoomSpec spec;
    spec.sampleRate = kSr;
    as::analysis::WaveSource src;
    src.name = "test";
    const Stereo s = sine(0.1, 440.0, 0.5);
    src.L = s.L;
    src.R = s.R;
    src.centre = 2400;
    src.L[2400] += 0.2f;
    spec.sources.push_back(src);
    spec.title = "zoom test";
    spec.markers.push_back({0.0, "click"});
    as::analysis::renderWaveZoom(spec, dir + "/zoom.png");
    spec.showR = false;
    spec.halfMs = 2.0;
    spec.sources.push_back(src);
    as::analysis::renderWaveZoom(spec, dir + "/zoom_left.png");
    int w = 0, h = 0, w2 = 0, h2 = 0;
    check(validPng(dir + "/zoom.png", w, h) && w == 1600 && h > 500 && validPng(dir + "/zoom_left.png", w2, h2) && w2 == 1600,
          "waveform zoom PNGs (L+R, left only with two sources) written and valid");
}

}  // namespace

int main(int argc, char** argv) {
    const std::string dir = argc > 1 ? argv[1] : (fs::temp_directory_path() / "agentsound_test_clicks").string();
    fs::create_directories(dir);
    try {
        testWavReader(dir);
        testTruePositives();
        testNoFalsePositives();
        testRealClicks();
        testAnalyzerClicksAndImages(dir);
        testZoomImage(dir);
    } catch (const std::exception& e) {
        std::printf("[FAIL] exception: %s\n", e.what());
        ++failures;
    }
    std::printf("%s: %d failure(s); images in %s\n", failures ? "FAILED" : "PASSED", failures, dir.c_str());
    return failures ? 1 : 0;
}
