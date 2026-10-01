// Tests for engine/analysis: BS.1770 / EBU conformance, true peak, band split, report warnings,
// PNG encoder/decoder. Usage: test_analysis [outDir]  (sample PNGs + report are written there;
// default: <temp>/agentsound_test_analysis).

#include "analysis/Canvas.h"
#include "analysis/Fft.h"
#include "analysis/Loudness.h"
#include "analysis/MixAnalyzer.h"
#include "analysis/MixImpl.h"
#include "analysis/Png.h"
#include "analysis/Profiles.h"
#include "analysis/StreamStats.h"
#include "dsp/Dsp.h"
#include "render/SongSpec.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <functional>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;
using as::json;
constexpr double kPi = 3.14159265358979323846;
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
    void append(const Stereo& o) {
        L.insert(L.end(), o.L.begin(), o.L.end());
        R.insert(R.end(), o.R.begin(), o.R.end());
    }
};

// Sine with peak amplitude given in dBFS (EBU convention: full-scale sine = 0 dBFS).
Stereo sine(double sr, double seconds, double hz, double dbfs, bool left = true, bool right = true, double phase = 0.0) {
    Stereo s;
    const auto n = static_cast<std::size_t>(seconds * sr);
    s.L.resize(n);
    s.R.resize(n);
    const double a = std::pow(10.0, dbfs / 20.0);
    for (std::size_t i = 0; i < n; ++i) {
        const auto v = static_cast<float>(a * std::sin(2.0 * kPi * hz * static_cast<double>(i) / sr + phase));
        s.L[i] = left ? v : 0.0f;
        s.R[i] = right ? v : 0.0f;
    }
    return s;
}

Stereo silence(double sr, double seconds) {
    Stereo s;
    s.L.assign(static_cast<std::size_t>(seconds * sr), 0.0f);
    s.R = s.L;
    return s;
}

// Feeds a mix (and optional nodes) in 256-frame blocks like the renderer, returns the report.
json analyse(as::MixAnalyzer& an, double sr, const Stereo& mix, const std::vector<Stereo>& nodes = {},
             const std::vector<std::string>& ids = {}, std::vector<as::SectionMarker> sections = {}, double bpm = 120.0,
             const std::vector<bool>& buses = {}, const std::function<void(as::MixAnalyzer&)>& setup = {},
             const std::function<void(as::MixAnalyzer&, const std::vector<int>&)>& afterAdd = {}) {
    an.prepare(sr, bpm, std::move(sections), static_cast<double>(mix.size()) / sr);
    if (setup) setup(an);
    std::vector<int> idx;
    for (std::size_t i = 0; i < nodes.size(); ++i) idx.push_back(an.addNode(ids[i], i < buses.size() && buses[i]));
    if (afterAdd) afterAdd(an, idx);
    for (std::size_t pos = 0; pos < mix.size(); pos += 256) {
        const int n = static_cast<int>(std::min<std::size_t>(256, mix.size() - pos));
        for (std::size_t k = 0; k < nodes.size(); ++k) an.feedNode(idx[k], nodes[k].L.data() + pos, nodes[k].R.data() + pos, n);
        an.feedMix(mix.L.data() + pos, mix.R.data() + pos, n);
    }
    return an.finish();
}

json analyseMix(double sr, const Stereo& mix) {
    as::MixAnalyzer an;
    return analyse(an, sr, mix);
}

// The mix analysed under an analysis profile (and an optional loudness override).
json analyseProfile(double sr, const Stereo& mix, const std::string& profile, const double* loudness = nullptr) {
    as::MixAnalyzer an;
    return analyse(an, sr, mix, {}, {}, {}, 120.0, {}, [&](as::MixAnalyzer& a) {
        a.setProfile(profile);
        if (loudness) a.setLoudnessTarget(loudness[0], loudness[1]);
    });
}

bool hasWarning(const json& r, const std::string& code, const std::vector<std::string>& nodes = {}) {
    for (const auto& w : r["warnings"]) {
        if (w["code"] != code) continue;
        bool all = true;
        for (const auto& n : nodes) {
            bool found = false;
            if (w.contains("nodes"))
                for (const auto& x : w["nodes"]) found = found || x == n;
            all = all && found;
        }
        if (all) return true;
    }
    return false;
}

// ------------------------------------------------------------------ unit tests

void testFft() {
    const int n = 64;
    as::analysis::Fft fft(n);
    std::vector<float> re(n), im(n), r0(n), i0(n);
    for (int i = 0; i < n; ++i) {
        re[static_cast<std::size_t>(i)] = r0[static_cast<std::size_t>(i)] = static_cast<float>(std::sin(i * 0.37) + 0.01 * i);
        im[static_cast<std::size_t>(i)] = i0[static_cast<std::size_t>(i)] = static_cast<float>(std::cos(i * 1.1));
    }
    fft.forward(re.data(), im.data());
    double err = 0.0;
    for (int k = 0; k < n; ++k) {
        std::complex<double> s = 0.0;
        for (int j = 0; j < n; ++j)
            s += std::complex<double>(r0[static_cast<std::size_t>(j)], i0[static_cast<std::size_t>(j)]) * std::polar(1.0, -2.0 * kPi * k * j / n);
        err = std::max(err, std::abs(s - std::complex<double>(re[static_cast<std::size_t>(k)], im[static_cast<std::size_t>(k)])));
    }
    check(err < 1e-4, fmt("FFT matches naive DFT (max error %.2g)", err));
}

void testChecksumsAndZlib() {
    const std::string s = "123456789";
    const auto* p = reinterpret_cast<const std::uint8_t*>(s.data());
    check(as::analysis::crc32(p, s.size()) == 0xCBF43926u, "CRC-32 check value of \"123456789\"");
    const std::string w = "Wikipedia";
    check(as::analysis::adler32(reinterpret_cast<const std::uint8_t*>(w.data()), w.size()) == 0x11E60398u, "Adler-32 of \"Wikipedia\"");

    as::dsp::Rng rng(12345);
    std::vector<std::uint8_t> noise(100000), text;
    for (auto& b : noise) b = static_cast<std::uint8_t>(rng.next() >> 56);
    for (int i = 0; i < 20000; ++i) text.push_back(static_cast<std::uint8_t>("the quick brown fox "[i % 20] + (i % 997 == 0)));
    for (const auto* data : {&noise, &text}) {
        const auto z = as::analysis::zlibCompress(data->data(), data->size());
        const auto u = as::analysis::zlibDecompress(z.data(), z.size());
        check(u == *data, fmt("zlib round trip (%.0f -> %.0f bytes)", static_cast<double>(data->size()), static_cast<double>(z.size())));
    }
    std::vector<std::uint8_t> empty;
    const auto ze = as::analysis::zlibCompress(empty.data(), 0);
    check(as::analysis::zlibDecompress(ze.data(), ze.size()).empty(), "zlib round trip of empty input");
    auto bad = as::analysis::zlibCompress(text.data(), text.size());
    bad[bad.size() / 2] ^= 0x55;
    bool threw = false;
    try { (void)as::analysis::zlibDecompress(bad.data(), bad.size()); } catch (const std::exception&) { threw = true; }
    check(threw, "corrupted zlib stream is rejected");
}

void testPngRoundTrip(const std::string& outDir) {
    using namespace as::analysis;
    Canvas c(321, 123, rgbHex(0x101218));
    for (int x = 0; x < 321; ++x)
        for (int y = 60; y < 123; ++y) c.set(x, y, inferno(x / 320.0));
    c.text(4, 4, "AgentSound 0123456789 -14.2 LUFS gjpqy_ {}", rgbHex(0xffffff), 1);
    c.text(4, 20, "Hello bass/kick", rgbHex(0xffb020), 2);
    c.line(0, 122, 320, 60, rgbHex(0x55ccff), 3);
    const auto png = encodePng(c.image());
    const Image back = decodePng(png);
    check(back.width == 321 && back.height == 123 && back.rgb == c.image().rgb, "PNG encode -> decode is pixel exact");
    auto corrupt = png;
    corrupt[40] ^= 0x01;  // inside IHDR/IDAT data -> CRC mismatch
    bool threw = false;
    try { (void)decodePng(corrupt); } catch (const std::exception&) { threw = true; }
    check(threw, "PNG with a corrupted chunk is rejected (CRC check)");
    writePng(outDir + "/font_test.png", c.image());
}

void testKWeighting() {
    const as::analysis::KWeighting k(48000.0);
    const double e = std::max({std::fabs(k.shelf.b0 - 1.53512485958697), std::fabs(k.shelf.b1 + 2.69169618940638),
                               std::fabs(k.shelf.b2 - 1.19839281085285), std::fabs(k.shelf.a1 + 1.69065929318241),
                               std::fabs(k.shelf.a2 - 0.73248077421585), std::fabs(k.highpass.a1 + 1.99004745483398),
                               std::fabs(k.highpass.a2 - 0.99007225036621)});
    check(e < 1e-10, fmt("K-weighting coefficients at 48 kHz match BS.1770-4 (max diff %.1g)", e));
}

// ------------------------------------------------------------------ loudness conformance

void testLoudness() {
    const double sr = 48000.0;
    struct Case { const char* name; std::vector<std::pair<double, double>> parts; double expect; };
    // EBU Tech 3341 cases 1-4 (1 kHz stereo sine, level in dBFS, duration in s).
    const std::vector<Case> cases = {
        {"EBU 3341 #1: -23 dBFS 1 kHz stereo, 20 s", {{-23, 20}}, -23.0},
        {"EBU 3341 #2: -33 dBFS 1 kHz stereo, 20 s", {{-33, 20}}, -33.0},
        {"EBU 3341 #3: -36/-23/-36 dBFS (10/60/10 s)", {{-36, 10}, {-23, 60}, {-36, 10}}, -23.0},
        {"EBU 3341 #4: -72/-36/-23/-36/-72 dBFS", {{-72, 10}, {-36, 10}, {-23, 60}, {-36, 10}, {-72, 10}}, -23.0},
    };
    for (const auto& c : cases) {
        Stereo s;
        for (auto [db, sec] : c.parts) s.append(sine(sr, sec, 1000.0, db));
        const json r = analyseMix(sr, s);
        const double i = r["global"]["lufsIntegrated"];
        check(std::fabs(i - c.expect) <= 0.1, std::string(c.name) + fmt(" -> I = %.2f LUFS (expect %.1f)", i, c.expect));
        if (c.parts.size() == 1) {
            const double m = r["global"]["momentaryMax"], st = r["global"]["shortTermMax"];
            check(std::fabs(m - c.expect) <= 0.1 && std::fabs(st - c.expect) <= 0.1,
                  fmt("  momentary max %.1f / short-term max %.1f LUFS", m, st));
        }
    }
    {
        const json r = analyseMix(sr, sine(sr, 10.0, 997.0, 0.0, true, false));
        const double i = r["global"]["lufsIntegrated"];
        check(std::fabs(i + 3.01) <= 0.05, fmt("0 dBFS 997 Hz in one channel -> %.2f LUFS (expect -3.01)", i));
    }
    for (double fs : {44100.0, 96000.0}) {
        const json r = analyseMix(fs, sine(fs, 10.0, 1000.0, -23.0));
        const double i = r["global"]["lufsIntegrated"];
        check(std::fabs(i + 23.0) <= 0.1, fmt("-23 dBFS 1 kHz at %.0f Hz -> %.2f LUFS", fs, i));
    }
    {   // Gating: silence around the programme must not change integrated loudness.
        Stereo prog;  // long enough that the few partial blocks at the edges do not matter
        prog.append(sine(sr, 20.0, 440.0, -18.0));
        prog.append(sine(sr, 20.0, 2500.0, -24.0));
        Stereo padded = silence(sr, 20.0);
        padded.append(prog);
        padded.append(silence(sr, 20.0));
        const double a = analyseMix(sr, prog)["global"]["lufsIntegrated"];
        const double b = analyseMix(sr, padded)["global"]["lufsIntegrated"];
        check(std::fabs(a - b) <= 0.1 + 1e-6, fmt("gating: programme %.2f LUFS, silence-padded %.2f LUFS", a, b));
    }
    {   // EBU Tech 3342 loudness range.
        Stereo s1 = sine(sr, 20.0, 1000.0, -20.0);
        s1.append(sine(sr, 20.0, 1000.0, -30.0));
        const double l1 = analyseMix(sr, s1)["global"]["loudnessRange"];
        check(std::fabs(l1 - 10.0) <= 1.0, fmt("EBU 3342 #1 (-20/-30 dBFS) LRA = %.1f LU (expect 10 +-1)", l1));
        Stereo s4;
        for (double db : {-50.0, -35.0, -20.0, -35.0, -50.0}) s4.append(sine(sr, 20.0, 1000.0, db));
        const double l4 = analyseMix(sr, s4)["global"]["loudnessRange"];
        check(std::fabs(l4 - 15.0) <= 1.0, fmt("EBU 3342 #4 (-50/-35/-20/-35/-50 dBFS) LRA = %.1f LU (expect 15 +-1)", l4));
    }
}

void testTruePeak() {
    const double sr = 48000.0;
    // fs/4 sine, 45 deg phase: samples sit at +-0.707 * A, the true peak A lies between samples.
    // 20 ms fades keep the abrupt start/end from ringing above A.
    Stereo s = sine(sr, 2.0, sr / 4.0, -6.0, true, true, kPi / 4.0);
    const auto fade = static_cast<std::size_t>(0.02 * sr);
    for (std::size_t i = 0; i < fade; ++i) {
        const auto g = static_cast<float>(0.5 - 0.5 * std::cos(kPi * static_cast<double>(i) / fade));
        s.L[i] *= g; s.R[i] *= g;
        s.L[s.size() - 1 - i] *= g; s.R[s.size() - 1 - i] *= g;
    }
    const json r = analyseMix(sr, s);
    const double tp = r["global"]["truePeakDbtp"], sp = r["global"]["samplePeakDb"];
    check(std::fabs(tp + 6.0) <= 0.3 && std::fabs(sp + 9.0) <= 0.1,
          fmt("true peak of fs/4 sine at 45 deg: TP %.2f dBTP (expect -6.0 +-0.3), sample peak %.2f dBFS", tp, sp));
    const json r2 = analyseMix(sr, sine(sr, 2.0, 997.0, -0.5));
    const double tp2 = r2["global"]["truePeakDbtp"];
    check(std::fabs(tp2 + 0.5) <= 0.1, fmt("true peak of a -0.5 dBFS 997 Hz sine: %.2f dBTP", tp2));
    check(hasWarning(r2, "true_peak"), "true peak above -1 dBTP is flagged");

    Stereo hot = sine(sr, 2.0, 200.0, 3.0);  // clips
    const json r3 = analyseMix(sr, hot);
    check(r3["global"]["clippedSamples"].get<long long>() > 0 && hasWarning(r3, "clipping"), "clipping is counted and flagged");
}

void testBandsAndStereo() {
    const double sr = 48000.0;
    {
        const json r = analyseMix(sr, sine(sr, 4.0, 100.0, -12.0));
        const double bass = r["global"]["bandsPct"]["bass"];
        check(bass > 95.0, fmt("100 Hz sine lands in 'bass' (%.1f %% of energy)", bass));
        const double c = r["global"]["stereoCorrelation"];
        check(c > 0.99, fmt("identical L/R -> correlation %.2f", c));
    }
    {
        const json r = analyseMix(sr, sine(sr, 4.0, 40.0, -12.0));
        check(r["global"]["bandsPct"]["sub"].get<double>() > 90.0, "40 Hz sine lands in 'sub'");
        const json r2 = analyseMix(sr, sine(sr, 4.0, 4000.0, -12.0));
        check(r2["global"]["bandsPct"]["presence"].get<double>() > 95.0, "4 kHz sine lands in 'presence'");
    }
    {   // Anti-phase bass: low end not mono, phase problem.
        Stereo s = sine(sr, 6.0, 70.0, -12.0);
        for (auto& v : s.R) v = -v;
        const json r = analyseMix(sr, s);
        check(r["global"]["lowEndCorrelation"].get<double>() < -0.9, "anti-phase 70 Hz -> low-end correlation ~ -1");
        check(hasWarning(r, "low_end_not_mono") && hasWarning(r, "phase"), "anti-phase low end is flagged (low_end_not_mono, phase)");
    }
}

// ------------------------------------------------------------------ report-level tests

void testMaskingAndWarnings() {
    const double sr = 48000.0, secs = 16.0;
    // Two tracks with identical low-frequency content, a quiet pad, a near-silent track.
    Stereo bassA = sine(sr, secs, 80.0, -14.0), bassB = sine(sr, secs, 80.0, -14.0);
    Stereo pad = sine(sr, secs, 1200.0, -20.0);
    Stereo ghost = sine(sr, secs, 1200.0, -58.0);  // -61 dB RMS: silent track
    Stereo whisper = sine(sr, secs, 300.0, -45.0);  // audible level but < 1 % of every band
    for (std::size_t i = 0; i < pad.size(); ++i) { pad.R[i] *= 0.7f; }
    Stereo mix;
    mix.L.resize(bassA.size());
    mix.R.resize(bassA.size());
    for (std::size_t i = 0; i < mix.size(); ++i) {
        mix.L[i] = bassA.L[i] + bassB.L[i] + pad.L[i] + ghost.L[i] + whisper.L[i];
        mix.R[i] = bassA.R[i] + bassB.R[i] + pad.R[i] + ghost.R[i] + whisper.R[i];
    }
    as::MixAnalyzer an;
    const std::vector<as::SectionMarker> sections = {{"verse", 0.0, 8.0}, {"chorus", 8.0, 16.0}};
    const json r = analyse(an, sr, mix, {bassA, bassB, pad, ghost, whisper}, {"bass", "sub_bass", "pad", "ghost", "whisper"}, sections);
    check(hasWarning(r, "masking", {"bass", "sub_bass"}), "masking warning names both tracks with identical low end");
    check(!hasWarning(r, "masking", {"pad"}), "no masking warning for the pad");
    check(hasWarning(r, "silent_node", {"ghost"}), "track that never exceeds -50 dBFS is reported as silent");
    check(hasWarning(r, "inaudible", {"whisper"}), "track contributing < 1 % everywhere is reported as nearly inaudible");
    bool suggestion = false;
    for (const auto& s : r["suggestions"]) suggestion = suggestion || s.get<std::string>().find("sub_bass") != std::string::npos;
    check(suggestion, "a suggestion addresses the masking pair");
    check(r["sections"].size() == 2 && r["sections"][0]["name"] == "verse", "per-section entries are reported");
    check(r["sections"][0]["active"].size() >= 3, "active nodes are listed per section");
    const auto& n0 = r["nodes"][0];
    check(n0["id"] == "bass" && n0["dominantBand"] == "bass" && std::fabs(n0["mixSharePct"]["bass"].get<double>() - 50.0) < 2.0,
          fmt("node stats: 'bass' dominant band bass, %.1f %% share of the bass band", n0["mixSharePct"]["bass"].get<double>()));
    const double rms = n0["rmsDb"];
    check(std::fabs(rms - (-17.0)) < 0.2, fmt("node rmsDb of a -14 dBFS-peak sine = %.2f (expect -17.0)", rms));
    const double lufsNode = n0["lufs"];
    check(std::isfinite(lufsNode) && lufsNode < -10.0 && lufsNode > -30.0, fmt("node lufs estimate %.1f", lufsNode));
    const auto& tl = r["timeline"];
    check(tl["rows"].size() == 8 && tl["rows"][0].size() == tl["columns"].size(), "timeline: one row per bar (8 bars at 120 bpm)");
    check(n0["barsRmsDb"].size() == 8, "node barsRmsDb has one entry per bar");

    // Silent section and level jump.
    Stereo s = sine(sr, 8.0, 500.0, -12.0);
    s.append(silence(sr, 8.0));
    s.append(sine(sr, 8.0, 500.0, -30.0));
    as::MixAnalyzer an2;
    const json r2 = analyse(an2, sr, s, {}, {}, {{"loud", 0, 8}, {"gap", 8, 16}, {"quiet", 16, 24}, {"after_end", 30, 40}});
    check(hasWarning(r2, "silent_section"), "silent section is flagged");
    check(hasWarning(r2, "section_out_of_range"), "section after the end of the audio is flagged");
    Stereo j = sine(sr, 8.0, 500.0, -30.0);
    j.append(sine(sr, 8.0, 500.0, -12.0));
    as::MixAnalyzer an3;
    const json r3 = analyse(an3, sr, j, {}, {}, {{"verse", 0, 8}, {"drop", 8, 16}});
    check(hasWarning(r3, "level_jump"), "18 LU jump between sections is flagged");

    // formatReport output is valid JSON with the same content.
    const std::string text = as::formatReport(r);
    check(json::parse(text) == r, "formatReport() produces equivalent, parseable JSON");
}

void testExactBoundaries() {
    // A track that plays exactly one bar at 123 bpm (bar edges fall inside 100 ms ticks): the bars
    // and sections around it must read as silent, not leak part of the neighbouring bar.
    const double sr = 48000.0, bpm = 123.0;
    auto bar = [&](int b) { return static_cast<std::size_t>(as::analysis::barStartSample(b, 0.0, bpm, sr)); };
    const std::size_t n = bar(4);
    Stereo node;
    node.L.assign(n, 0.0f);
    node.R.assign(n, 0.0f);
    for (std::size_t i = bar(1); i < bar(2); ++i)
        node.L[i] = node.R[i] = static_cast<float>(0.25 * std::sin(2.0 * kPi * 55.0 * static_cast<double>(i) / sr));
    const double barSec = 240.0 / bpm;
    as::MixAnalyzer an;
    const json r = analyse(an, sr, node, {node}, {"bassline"}, {{"a", 0.0, barSec}, {"b", barSec, 2 * barSec}, {"c", 2 * barSec, 4 * barSec}}, bpm);
    const auto& bars = r["nodes"][0]["barsRmsDb"];
    check(bars.size() == 4 && bars[0] == -120 && bars[2] == -120 && std::abs(bars[1].get<int>() + 15) <= 1,
          "per-bar node RMS is sample exact at bar edges (" + bars.dump() + ")");
    const auto& secs = r["nodes"][0]["sections"];
    check(secs[0]["rmsDb"] == -120.0 && secs[2]["rmsDb"] == -120.0 && std::fabs(secs[1]["rmsDb"].get<double>() + 15.1) < 0.2,
          "per-section node RMS is sample exact at section edges (" + secs.dump() + ")");
    const auto& rows = r["timeline"]["rows"];
    // Bar 3 only holds the K-weighting filter's ring-out (~ -50 LUFS), as in any BS.1770 meter.
    check(rows[0][2] == -120.0 && rows[2][2].get<double>() < -45.0 && rows[0][5] == -120 && rows[2][5] == -120 &&
              rows[1][5].get<int>() > -20,
          "timeline rows next to the active bar stay silent (no spectral leakage): " + rows[0].dump() + " " + rows[2].dump());

    // Preview render starting at song beat 6: bars keep the song's numbering.
    as::MixAnalyzer an2;
    an2.prepare(sr, 120.0, {}, 4.0);
    an2.setStartBeat(6.0);
    const Stereo s = sine(sr, 4.0, 440.0, -20.0);
    for (std::size_t pos = 0; pos < s.size(); pos += 256) {
        const int k = static_cast<int>(std::min<std::size_t>(256, s.size() - pos));
        an2.feedMix(s.L.data() + pos, s.R.data() + pos, k);
    }
    const json r2 = an2.finish();
    check(r2["timeline"]["rows"][0][0] == 2 && r2["timeline"]["rows"].size() == 3, "setStartBeat(6): timeline starts at song bar 2");
}

void testEdgeCases(const std::string& outDir) {
    const double sr = 48000.0;
    {   // Nothing fed at all.
        as::MixAnalyzer an;
        an.prepare(sr, 120.0, {{"intro", 0.0, 4.0}}, 0.0);
        an.addNode("never_fed", false);
        const json r = an.finish();
        an.writeSpectrogramPng(outDir + "/empty_spectrogram.png");
        an.writeOverviewPng(outDir + "/empty_overview.png");
        fs::create_directories(outDir + "/empty");
        an.writeImages(outDir + "/empty");
        bool all = true;
        for (const auto& im : r["images"]) all = all && fs::exists(outDir + "/empty/" + im["file"].get<std::string>());
        check(hasWarning(r, "no_audio") && r["global"]["lufsIntegrated"] == -120.0 && r["images"].size() >= 6 && all && r["clicks"].empty(),
              "empty render: report + every image, 'no_audio' error, no clicks");
    }
    {   // 10 ms of audio, NaN/Inf in a node and in the mix.
        Stereo s = sine(sr, 0.01, 1000.0, -6.0);
        Stereo bad = s;
        bad.L[10] = std::numeric_limits<float>::quiet_NaN();
        bad.R[20] = std::numeric_limits<float>::infinity();
        as::MixAnalyzer an;
        const json r = analyse(an, sr, bad, {bad}, {"unstable"});
        an.writeOverviewPng(outDir + "/short_overview.png");
        fs::create_directories(outDir + "/short");
        an.writeImages(outDir + "/short");
        bool all = r["images"].size() >= 6;
        for (const auto& im : r["images"]) all = all && fs::exists(outDir + "/short/" + im["file"].get<std::string>());
        check(all, "10 ms render: every listed image written");
        const std::string text = r.dump();
        check(text.find("null") == std::string::npos,  // nlohmann writes NaN/Inf as null
              "10 ms render with NaN/Inf input: every number in the report is finite");
        check(hasWarning(r, "non_finite", {"unstable"}), "non-finite node samples are reported");
        check(std::fabs(r["global"]["samplePeakDb"].get<double>() + 6.0) < 0.1, "non-finite mix samples are ignored for peaks");
    }
}

// ------------------------------------------------------------------ review fixes

// One sine per band at the band's geometric centre, energies following the reference balance;
// `boostDb` raises one band's level.
Stereo referenceTones(double sr, double seconds, int boostBand, double boostDb,
                      const std::array<double, as::analysis::kNumBands>& ref = as::analysis::referenceBandShares()) {
    const double hz[as::analysis::kNumBands] = {35, 122, 450, 1400, 3900, 8500, 15500};
    Stereo s = silence(sr, seconds);
    for (int b = 0; b < as::analysis::kNumBands; ++b) {
        const double power = 0.05 * ref[static_cast<std::size_t>(b)] * (b == boostBand ? std::pow(10.0, boostDb / 10.0) : 1.0);
        const double amp = std::sqrt(2.0 * power);
        for (std::size_t i = 0; i < s.size(); ++i) {
            const auto v = static_cast<float>(amp * std::sin(2.0 * kPi * hz[b] * static_cast<double>(i) / sr + b));
            s.L[i] += v;
            s.R[i] += v;
        }
    }
    return s;
}

void testReviewFixes() {
    const double sr = 48000.0;
    {   // Balance vs reference is a level (median-aligned), not a saturating share ratio.
        const json flat = analyseMix(sr, referenceTones(sr, 6.0, -1, 0.0));
        double maxDev = 0.0;
        for (const auto& [k, v] : flat["global"]["bandsVsRefDb"].items()) maxDev = std::max(maxDev, std::fabs(v.get<double>()));
        check(maxDev < 0.5, fmt("reference-shaped tones read ~0 dB vs reference in every band (max |dev| %.2f)", maxDev));
        const json boom = analyseMix(sr, referenceTones(sr, 6.0, 1, 6.0));
        const double bass = boom["global"]["bandsVsRefDb"]["bass"], mid = boom["global"]["bandsVsRefDb"]["mid"];
        check(std::fabs(bass - 6.0) < 0.5 && std::fabs(mid) < 0.5,
              fmt("+6 dB on the 45 %% bass band reads bass %+.1f dB, mid %+.1f dB (share ratio said +2.3)", bass, mid));
        check(hasWarning(boom, "balance_bass_high"), "boomy low end (+6 dB bass) is flagged (rule was unreachable before)");
        check(!hasWarning(flat, "balance_bass_high") && !hasWarning(flat, "balance_sub_high"), "reference-shaped mix raises no balance warning");
    }
    {   // L/R balance, merged DC warning, squashed PLR.
        Stereo s = sine(sr, 6.0, 440.0, -6.0);
        for (auto& v : s.R) v *= 0.7079f;  // -3 dB
        for (auto& v : s.L) v += 0.01f;
        as::MixAnalyzer an;
        const json r = analyse(an, sr, s, {s}, {"lead"});
        const double bal = r["global"]["balanceLrDb"], nodeBal = r["nodes"][0]["balanceLrDb"];
        check(std::fabs(bal - 3.0) < 0.2 && std::fabs(nodeBal - 3.0) < 0.2 && hasWarning(r, "lr_balance", {}),
              fmt("left 3 dB louder: balanceLrDb %.1f (node %.1f) and lr_balance flagged", bal, nodeBal));
        int dc = 0;
        for (const auto& w : r["warnings"]) dc += w["code"] == "dc_offset";
        check(dc == 1, "DC offset on both channels gives one dc_offset warning");
        check(hasWarning(r, "squashed"), fmt("sine master (PLR %.1f dB) is flagged as squashed", r["global"]["plr"].get<double>()));
    }
    {   // Two parts sharing the air band: info, not a masking warning.
        const Stereo a = sine(sr, 8.0, 15000.0, -20.0), b = sine(sr, 8.0, 15000.0, -20.0);
        Stereo mix = a;
        for (std::size_t i = 0; i < mix.size(); ++i) { mix.L[i] += b.L[i]; mix.R[i] += b.R[i]; }
        as::MixAnalyzer an;
        const json r = analyse(an, sr, mix, {a, b}, {"hats", "shaker"});
        bool info = false, warn = false;
        for (const auto& w : r["warnings"])
            if (w["code"] == "masking") (w["severity"] == "info" ? info : warn) = true;
        check(info && !warn, "air-band overlap of two parts is reported as info, not a masking warning");
    }
    {   // Kick vs bass: sustained bass masks, a bass ducked under every kick (sidechain) alternates.
        const double bpm = 120.0, beat = 60.0 / bpm, secs = 16.0;
        const auto n = static_cast<std::size_t>(secs * sr);
        Stereo kick = silence(sr, secs), flat = silence(sr, secs), ducked = silence(sr, secs);
        double ph = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            const double t = static_cast<double>(i) / sr, ib = std::fmod(t, beat);
            ph += 2.0 * kPi * (48.0 + 90.0 * std::exp(-ib * 35.0)) / sr;
            kick.L[i] = kick.R[i] = static_cast<float>(0.7 * std::exp(-ib * 9.0) * std::sin(ph));
            const double b = 0.2 * std::sin(2.0 * kPi * 49.0 * t);
            const double duck = 1.0 - 0.8 * std::exp(-ib / 0.12);  // -14 dB at the hit, 120 ms recovery
            flat.L[i] = flat.R[i] = static_cast<float>(b);
            ducked.L[i] = ducked.R[i] = static_cast<float>(b * duck);
        }
        for (int variant = 0; variant < 2; ++variant) {
            const Stereo& bass = variant ? ducked : flat;
            Stereo mix = kick;
            for (std::size_t i = 0; i < n; ++i) { mix.L[i] += bass.L[i]; mix.R[i] += bass.R[i]; }
            as::MixAnalyzer an;
            const json r = analyse(an, sr, mix, {kick, bass}, {"kick", "bass"}, {{"verse", 0, 8}, {"chorus", 8, 16}}, bpm);
            std::string sev = "none", msg;
            for (const auto& w : r["warnings"])
                if (w["code"] == "masking") { sev = w["severity"]; msg = w["message"]; }
            if (variant == 0)
                check(sev == "warn", "kick over an unducked sustained bass: masking warning (" + msg + ")");
            else
                check(sev == "info" && msg.find("alternate") != std::string::npos,
                      "kick over a sidechain-ducked bass: recognised as alternating, info only (" + msg + ")");
        }
    }
    {   // A loud section must not leak into the next section's short-term maximum.
        Stereo s = sine(sr, 8.0, 1000.0, -10.0);
        s.append(sine(sr, 8.0, 1000.0, -30.0));
        as::MixAnalyzer an;
        const json r = analyse(an, sr, s, {}, {}, {{"chorus", 0, 8}, {"outro", 8, 16}});
        const double st = r["sections"][1]["shortTermMax"];
        check(std::fabs(st + 30.0) < 0.5, fmt("quiet outro after a loud chorus: shortTermMax %.1f LUFS (expect -30)", st));
    }
    {   // Low sample rate: every 100 ms tick still gets a spectral split.
        const json r = analyseMix(8000.0, sine(8000.0, 4.0, 100.0, -12.0));
        bool ok = r["global"]["bandsPct"]["bass"].get<double>() > 95.0;
        for (const auto& row : r["timeline"]["rows"]) ok = ok && row[6].get<int>() > -20;  // bass column
        check(ok, "8 kHz: 100 Hz sine is 'bass' in every timeline bar");
    }
    {   // API misuse is rejected instead of silently misaligning timelines.
        as::MixAnalyzer an;
        an.prepare(sr, 120.0, {}, 1.0);
        const Stereo s = sine(sr, 0.1, 440.0, -20.0);
        an.feedMix(s.L.data(), s.R.data(), static_cast<int>(s.size()));
        bool threwAdd = false, threwBeat = false;
        try { an.addNode("late", false); } catch (const std::logic_error&) { threwAdd = true; }
        try { an.setStartBeat(4.0); } catch (const std::logic_error&) { threwBeat = true; }
        check(threwAdd && threwBeat, "addNode / setStartBeat after feeding started throw std::logic_error");
    }
    {   // formatReport: reading order and one entry per line for text lists.
        Stereo s = sine(sr, 4.0, 60.0, -3.0);
        const json r = analyseMix(sr, s);
        const std::string t = as::formatReport(r);
        const auto pSummary = t.find("\"summary\""), pWarn = t.find("\"warnings\""), pGlobal = t.find("\"global\"");
        check(pSummary < pWarn && pWarn < pGlobal && t.find("{\"severity\":") != std::string::npos,
              "formatReport: summary, warnings, then global; warnings start with severity");
        check(t.find("\n    \"bands\": ") != std::string::npos && t.find("\"suggestions\": [\n") != std::string::npos,
              "formatReport: glossary and suggestions get one entry per line");
        check(json::parse(t) == r, "formatReport output still parses to the same report");
    }
}

// ------------------------------------------------------------------ analysis profiles

double bandVsRef(const json& r, const char* band) { return r["global"]["bandsVsRefDb"][band].get<double>(); }

bool anyBalanceWarning(const json& r) {
    for (const auto& w : r["warnings"])
        if (w["code"].get<std::string>().rfind("balance_", 0) == 0) return true;
    return false;
}

void testProfiles() {
    namespace an = as::analysis;
    const double sr = 48000.0;
    {   // Registry: every profile, default first and identical to the old reference.
        check(an::analysisProfileNames() == "default, synthwave, dreamwave, darksynth, jazz, classical, piano, pop, rock, film",
              "profiles: " + an::analysisProfileNames());
        check(an::findAnalysisProfile("outrun") == nullptr && an::findAnalysisProfile("synthwave") != nullptr,
              "findAnalysisProfile: unknown names give nullptr");
        const auto def = an::defaultAnalysisProfile().bandShares(), old = an::referenceBandShares();
        bool same = true, sums = true;
        for (int b = 0; b < an::kNumBands; ++b) same = same && def[static_cast<std::size_t>(b)] == old[static_cast<std::size_t>(b)];
        for (const auto& p : an::analysisProfiles()) {
            double s = 0.0;
            for (double v : p.bandShares()) s += v;
            sums = sums && std::fabs(s - 1.0) < 1e-12 && p.lufsMin < p.lufsMax;
        }
        check(same && sums, "default profile = the previous reference curve; every profile's band shares sum to 1");
        const auto* sw = an::findAnalysisProfile("synthwave");
        const auto* dw = an::findAnalysisProfile("dreamwave");
        const auto* ds = an::findAnalysisProfile("darksynth");
        const auto s = sw->bandShares(), w = dw->bandShares(), k = ds->bandShares();
        check(s[0] > 2.5 * def[0] && s[0] > 0.25 && s[0] < 0.4,
              fmt("synthwave reference: sub %.1f %% of the energy (default %.1f %%)", 100 * s[0], 100 * def[0]));
        check(w[4] / w[3] < def[4] / def[3] && k[2] / k[3] > def[2] / def[3],
              "dreamwave has less presence, darksynth denser low mids (relative to the mids) than default");
        check(sw->lufsMin == -12 && sw->lufsMax == -9 && dw->lufsMin == -14 && dw->lufsMax == -10 && ds->lufsMin == -10 && ds->lufsMax == -7,
              "loudness targets: synthwave -12..-9, dreamwave -14..-10, darksynth -10..-7");
        as::MixAnalyzer a;
        a.prepare(sr, 120.0, {}, 1.0);
        std::string msg;
        try { a.setProfile("outrun"); } catch (const std::invalid_argument& e) { msg = e.what(); }
        check(msg.find("unknown analysis profile 'outrun'") != std::string::npos && msg.find("synthwave") != std::string::npos,
              "setProfile rejects unknown names and lists the profiles (" + msg + ")");
    }
    {   // The same four-on-the-floor-like mix (synthwave balance: ~31 % of the energy below 60 Hz):
        // 'sub high' under default, nothing under synthwave; a genuinely boomy one warns under both.
        const auto swShares = an::findAnalysisProfile("synthwave")->bandShares();
        const Stereo mix = referenceTones(sr, 6.0, -1, 0.0, swShares);
        const json def = analyseProfile(sr, mix, "default"), sw = analyseProfile(sr, mix, "synthwave");
        check(hasWarning(def, "balance_sub_high") && bandVsRef(def, "sub") > 5.0,
              fmt("synthwave-balanced mix under 'default': sub %+.1f dB -> balance_sub_high", bandVsRef(def, "sub")));
        double maxDev = 0.0;
        for (const auto& [b, v] : sw["global"]["bandsVsRefDb"].items()) maxDev = std::max(maxDev, std::fabs(v.get<double>()));
        check(!anyBalanceWarning(sw) && maxDev < 0.5,
              fmt("same mix under 'synthwave': every band ~0 dB (max |dev| %.2f), no balance warning", maxDev));
        bool hint = false;
        for (const auto& s : def["suggestions"]) hint = hint || s.get<std::string>().find("\"profile\": \"synthwave\"") != std::string::npos;
        check(hint, "'default' sub_high suggests trying the synthwave profile");
        const json boomy = analyseProfile(sr, referenceTones(sr, 6.0, 0, 7.0, swShares), "synthwave");
        check(hasWarning(boomy, "balance_sub_high"), fmt("+7 dB sub on top of the synthwave balance still warns under 'synthwave' "
                                                         "(sub %+.1f dB)", bandVsRef(boomy, "sub")));
        // The report states the profile everywhere and lists the thresholds it used.
        const json& ref = sw["reference"];
        check(ref["profile"] == "synthwave" && sw["summary"].get<std::string>().find("profile synthwave") != std::string::npos &&
                  def["reference"]["profile"] == "default" && ref["bandLimitsDb"]["sub"]["high"] == 5.0 &&
                  ref["bandLimitsDb"]["sub"]["low"] == -6.0 && def["reference"]["bandLimitsDb"]["sub"]["low"] == -9.0 &&
                  !ref["bandLimitsDb"]["lowmid"].contains("low") && ref["lufsTargetFrom"] == "profile" &&
                  std::fabs(ref["bandsPct"]["sub"].get<double>() - 100.0 * swShares[0]) < 0.06,
              "report.reference: profile name, band shares, band limits; summary names the profile");
        bool named = false;
        for (const auto& w : boomy["warnings"])
            if (w["code"] == "balance_sub_high") named = w["message"].get<std::string>().find("'synthwave' reference") != std::string::npos;
        check(named, "balance warnings name the profile they compare against");
        check(ref["profiles"] == json::array({"default", "synthwave", "dreamwave", "darksynth", "jazz", "classical", "piano", "pop",
                                              "rock", "film"}),
              "report.reference.profiles lists the profile names as an array");
        // Per-section balance follows the profile too (sections[].bandsVsRefDb).
        as::MixAnalyzer a;
        const json secs = analyse(a, sr, mix, {}, {}, {{"a", 0.0, 3.0}, {"b", 3.0, 6.0}}, 120.0, {},
                                  [](as::MixAnalyzer& x) { x.setProfile("synthwave"); });
        double secDev = 0.0;
        for (const auto& s : secs["sections"])
            for (const auto& [b, v] : s["bandsVsRefDb"].items()) secDev = std::max(secDev, std::fabs(v.get<double>()));
        check(secs["sections"].size() == 2 && secDev < 0.5, fmt("section balance vs the synthwave reference ~0 (max |dev| %.2f)", secDev));
    }
    {   // Loudness window per profile, and the explicit override (whatever the call order).
        const Stereo mix = sine(sr, 8.0, 1000.0, -12.5);  // ~ -12.5 LUFS
        const json def = analyseProfile(sr, mix, "default"), dream = analyseProfile(sr, mix, "dreamwave");
        const json dark = analyseProfile(sr, mix, "darksynth");
        check(hasWarning(def, "loudness_low") && !hasWarning(dream, "loudness_low") && !hasWarning(dream, "loudness_high") &&
                  hasWarning(dark, "loudness_low"),
              fmt("%.1f LUFS: too quiet for default/darksynth, fine for dreamwave (-14..-10)", def["global"]["lufsIntegrated"].get<double>()));
        check(dark["reference"]["lufsTarget"] == json::array({-10.0, -7.0}), "darksynth report target -10..-7");
        const double over[2] = {-13.0, -12.0};
        const json o = analyseProfile(sr, mix, "darksynth", over);
        as::MixAnalyzer a;
        const json o2 = analyse(a, sr, mix, {}, {}, {}, 120.0, {}, [](as::MixAnalyzer& x) {
            x.setLoudnessTarget(-13.0, -12.0);
            x.setProfile("darksynth");
        });
        check(!hasWarning(o, "loudness_low") && o["reference"]["lufsTarget"] == json::array({-13.0, -12.0}) &&
                  o["reference"]["lufsTargetFrom"] == "override" && o["reference"]["profileLufsTarget"] == json::array({-10.0, -7.0}) &&
                  o2["reference"]["lufsTarget"] == o["reference"]["lufsTarget"],
              "setLoudnessTarget overrides the profile window before or after setProfile");
    }
    {   // Peak-to-loudness ratio: a -20 dBFS tone with one louder cycle (PLR ~5.5 dB) is squashed
        // for default (>= 6 expected) but a normal loud master for darksynth (>= 5).
        Stereo s = sine(sr, 6.0, 1000.0, -20.0);
        const double g = std::pow(10.0, 5.5 / 20.0);
        for (std::size_t i = 144000; i < 144000 + 48; ++i) { s.L[i] *= static_cast<float>(g); s.R[i] *= static_cast<float>(g); }
        const json def = analyseProfile(sr, s, "default"), dark = analyseProfile(sr, s, "darksynth");
        check(hasWarning(def, "squashed") && !hasWarning(dark, "squashed"),
              fmt("PLR %.1f dB: squashed under default, fine under darksynth", def["global"]["plr"].get<double>()));
    }
}

// ------------------------------------------------------------------ synthetic song for visual checks

struct Song {
    Stereo mix;
    std::vector<Stereo> nodes;
    std::vector<std::string> ids;
    std::vector<bool> buses;
    std::vector<as::SectionMarker> sections;
    double bpm{104.0};
};

Song makeSong(double sr) {
    Song s;
    const double bpm = s.bpm, beat = 60.0 / bpm;
    const int bars = 32;
    const auto n = static_cast<std::size_t>(bars * 4 * beat * sr);
    const char* ids[] = {"kick", "bass", "snare", "hats", "pad", "lead_arp", "hall"};
    for (const char* id : ids) {
        s.ids.push_back(id);
        s.buses.push_back(std::string(id) == "hall");
        Stereo z;
        z.L.assign(n, 0.0f);
        z.R.assign(n, 0.0f);
        s.nodes.push_back(z);
    }
    auto& kick = s.nodes[0]; auto& bass = s.nodes[1]; auto& snare = s.nodes[2]; auto& hats = s.nodes[3];
    auto& pad = s.nodes[4]; auto& lead = s.nodes[5]; auto& hall = s.nodes[6];
    as::dsp::Rng rng(7);
    auto barOf = [&](std::size_t i) { return static_cast<int>(static_cast<double>(i) / sr / (4 * beat)); };
    auto section = [&](int bar) { return bar < 4 ? 0 : bar < 12 ? 1 : bar < 20 ? 2 : bar < 24 ? 3 : 4; };  // intro verse chorus break chorus2
    const int chords[4][3] = {{57, 60, 64}, {53, 57, 60}, {55, 59, 62}, {52, 55, 59}};
    const int arp[8] = {0, 1, 2, 1, 2, 0, 1, 2};
    double padPh[3][2] = {}, bassPh = 0.0, leadPh = 0.0, kickPh = 0.0;
    as::dsp::OnePole hpHat, lpBass;
    lpBass.setLowPass(sr, 400.0);
    hpHat.setLowPass(sr, 7000.0);
    // A part that stops at a section change fades out over the last 8 ms before it (raised cosine,
    // no kinks) and the pad level glides (50 ms): cutting a sounding part dead is a click, which
    // the analyser (rightly) reports.
    const double barLen = 4 * beat, padCoef = 1.0 - std::exp(-1.0 / (0.05 * sr));
    auto partGain = [&](double t, int bar, bool (*on)(int)) {
        if (!on(section(bar))) return 0.0;
        const double toEnd = (bar + 1) * barLen - t, fade = 0.008;
        if (on(section(bar + 1)) || toEnd >= fade) return 1.0;
        return 0.5 * (1.0 - std::cos(kPi * std::max(0.0, toEnd) / fade));
    };
    static bool (*const kDrumsOn)(int) = [](int s) { return s == 1 || s == 2 || s == 4; };
    static bool (*const kBassOn)(int) = [](int s) { return s != 0 && s != 3; };
    static bool (*const kHatsOn)(int) = [](int s) { return s != 3; };
    static bool (*const kLeadOn)(int) = [](int s) { return s == 2 || s == 4; };
    double padLvl = 0.07;
    for (std::size_t i = 0; i < n; ++i) {
        const double t = static_cast<double>(i) / sr;
        const int bar = barOf(i), sec = section(bar);
        const double inBeat = std::fmod(t, beat), inSix = std::fmod(t, beat / 4.0);
        const int beatIdx = static_cast<int>(t / beat) % 4, sixIdx = static_cast<int>(t / (beat / 4.0)) % 16;
        const bool drums = sec == 1 || sec == 2 || sec == 4;
        const double gKick = partGain(t, bar, kDrumsOn), gBass = partGain(t, bar, kBassOn), gHats = partGain(t, bar, kHatsOn),
                     gLead = partGain(t, bar, kLeadOn);
        padLvl += padCoef * ((sec == 3 ? 0.05 : sec == 0 ? 0.07 : 0.045) - padLvl);
        // Kick: pitch-swept sine every beat.
        if (drums || gKick > 1e-6) {
            const double f = 45.0 + 110.0 * std::exp(-inBeat * 30.0);
            kickPh += 2 * kPi * f / sr;
            const auto v = static_cast<float>(gKick * 0.55 * std::exp(-inBeat * 7.0) * std::sin(kickPh));
            kick.L[i] = kick.R[i] = v;
        }
        // Bass: filtered saw on the chord root, ducked by the kick (3 ms fade into the duck, like the
        // engine's ducker: an instant 10 dB gain step would be a click on every beat).
        if ((sec != 0 && sec != 3) || gBass > 1e-6) {
            const double f = as::dsp::midiToHz(chords[bar % 4][0] - 24);
            bassPh = std::fmod(bassPh + f / sr, 1.0);
            const double duck = 1.0 - 0.7 * std::exp(-inBeat * 12.0) * std::min(1.0, inBeat / 0.003);
            const auto v = static_cast<float>(gBass * 0.35 * duck * lpBass.lowPass(static_cast<float>(2.0 * bassPh - 1.0)));
            bass.L[i] = bass.R[i] = v;
        }
        // Snare on 2 and 4: noise + tone.
        if (drums && (beatIdx == 1 || beatIdx == 3)) {
            const double env = std::exp(-inBeat * 18.0);
            const double v = env * (0.25 * rng.bipolar() + 0.15 * std::sin(2 * kPi * 190.0 * inBeat));
            snare.L[i] = static_cast<float>(v * 0.95);
            snare.R[i] = static_cast<float>(v * 1.05);
        }
        // Hats: 16ths of high-passed noise, panned right.
        if (sec != 3 || gHats > 1e-6) {
            const double env = gHats * std::exp(-inSix * (sixIdx % 4 == 2 ? 25.0 : 60.0));
            const float h = hpHat.highPass(rng.bipolar());
            hats.L[i] = static_cast<float>(0.10 * env * h * 0.6);
            hats.R[i] = static_cast<float>(0.10 * env * h);
        }
        // Pad: detuned saws (additive, band-limited), wide.
        {
            const double lvl = padLvl;
            double l = 0.0, r = 0.0;
            for (int v = 0; v < 3; ++v) {
                const double f = as::dsp::midiToHz(chords[bar % 4][v]);
                for (int side = 0; side < 2; ++side) {
                    padPh[v][side] = std::fmod(padPh[v][side] + f * (side ? 1.004 : 0.996) / sr, 1.0);
                    double saw = 0.0;
                    for (int h = 1; h <= 12; ++h) saw += std::sin(2 * kPi * h * padPh[v][side]) / h;
                    (side ? r : l) += saw;
                }
            }
            pad.L[i] = static_cast<float>(lvl * l / 3.0);
            pad.R[i] = static_cast<float>(lvl * r / 3.0);
        }
        // Lead arp in the choruses: square-ish, 16ths.
        if (sec == 2 || sec == 4 || gLead > 1e-6) {
            const double f = as::dsp::midiToHz(chords[bar % 4][arp[sixIdx % 8]] + 12);
            leadPh = std::fmod(leadPh + f / sr, 1.0);
            double sq = 0.0;
            for (int h = 1; h <= 15; h += 2) sq += std::sin(2 * kPi * h * leadPh) / h;
            const double env = gLead * std::exp(-inSix * 6.0);
            lead.L[i] = static_cast<float>(0.12 * env * sq);
            lead.R[i] = static_cast<float>(0.10 * env * sq);
        }
    }
    // Hall bus: crude multi-tap reverb of snare + pad.
    const int taps[6] = {1511, 2791, 4057, 6173, 8819, 12011};
    for (std::size_t i = 0; i < n; ++i) {
        double l = 0.0, r = 0.0;
        for (int k = 0; k < 6; ++k) {
            if (i < static_cast<std::size_t>(taps[k])) continue;
            const std::size_t j = i - static_cast<std::size_t>(taps[k]);
            const double g = 0.35 * std::pow(0.8, k);
            l += g * (snare.R[j] + 0.5 * pad.R[j]);
            r += g * (snare.L[j] + 0.5 * pad.L[j]);
        }
        hall.L[i] = static_cast<float>(l);
        hall.R[i] = static_cast<float>(r);
    }
    s.mix.L.assign(n, 0.0f);
    s.mix.R.assign(n, 0.0f);
    for (std::size_t i = 0; i < n; ++i) {
        double l = 0.0, r = 0.0;
        for (const auto& node : s.nodes) { l += node.L[i]; r += node.R[i]; }
        s.mix.L[i] = static_cast<float>(std::tanh(1.6 * l) / 1.6 * 1.25);  // gentle "master" saturation
        s.mix.R[i] = static_cast<float>(std::tanh(1.6 * r) / 1.6 * 1.25);
    }
    auto barSec = [&](int b) { return b * 4 * beat; };
    s.sections = {{"intro", barSec(0), barSec(4)}, {"verse", barSec(4), barSec(12)}, {"chorus", barSec(12), barSec(20)},
                  {"breakdown", barSec(20), barSec(24)}, {"chorus2", barSec(24), barSec(32)}};
    return s;
}

// ------------------------------------------------------------------ space (width / wetness / bed)

// Schroeder reverb (4 combs + 2 allpasses per side, different delays left/right: a decorrelated
// stereo tail with the given RT60) of a mono input.
Stereo schroeder(const std::vector<float>& in, double sr, double rt60) {
    struct Side {
        std::vector<std::vector<float>> comb, ap;
        std::vector<std::size_t> ci, ai;
        std::vector<float> fb;
    };
    auto makeSide = [&](int spread) {
        Side s;
        for (int d : {1557, 1617, 1491, 1422}) {
            const int len = d + spread;
            s.comb.emplace_back(static_cast<std::size_t>(len), 0.0f);
            s.fb.push_back(static_cast<float>(std::pow(10.0, -3.0 * len / (rt60 * sr))));
        }
        for (int d : {225 + spread / 2, 556 + spread / 3}) s.ap.emplace_back(static_cast<std::size_t>(d), 0.0f);
        s.ci.assign(4, 0);
        s.ai.assign(2, 0);
        return s;
    };
    Side sides[2] = {makeSide(0), makeSide(97)};
    Stereo out;
    out.L.resize(in.size());
    out.R.resize(in.size());
    for (std::size_t i = 0; i < in.size(); ++i) {
        for (int c = 0; c < 2; ++c) {
            Side& s = sides[c];
            float acc = 0.0f;
            for (std::size_t k = 0; k < 4; ++k) {
                float& z = s.comb[k][s.ci[k]];
                const float y = z;
                z = in[i] + y * s.fb[k];
                if (++s.ci[k] == s.comb[k].size()) s.ci[k] = 0;
                acc += y;
            }
            for (std::size_t k = 0; k < 2; ++k) {
                float& z = s.ap[k][s.ai[k]];
                const float y = z - 0.5f * acc;
                z = acc + 0.5f * y;
                if (++s.ai[k] == s.ap[k].size()) s.ai[k] = 0;
                acc = y;
            }
            (c ? out.R : out.L)[i] = 0.25f * acc;
        }
    }
    return out;
}

double kEnergy(const Stereo& s, double sr, std::size_t i0 = 0, std::size_t i1 = SIZE_MAX) {
    as::analysis::KWeighting kl(sr), kr(sr);
    double e = 0.0;
    for (std::size_t i = 0; i < s.size() && i < i1; ++i) {
        const double l = kl.process(s.L[i]), r = kr.process(s.R[i]);
        if (i >= i0) e += l * l + r * r;
    }
    return e;
}

void scale(Stereo& s, double g) {
    for (auto& v : s.L) v = static_cast<float>(v * g);
    for (auto& v : s.R) v = static_cast<float>(v * g);
}

Stereo sum(const std::vector<const Stereo*>& parts, std::size_t n) {
    Stereo s;
    s.L.assign(n, 0.0f);
    s.R.assign(n, 0.0f);
    for (const Stereo* p : parts)
        for (std::size_t i = 0; i < n && i < p->size(); ++i) { s.L[i] += p->L[i]; s.R[i] += p->R[i]; }
    return s;
}

// A small synthwave-like scene: kick + bass (mono), a pad (bed: whole notes, wide or centred), a lead
// (mono 8th-note line), a hall return (Schroeder reverb of pad + lead, optionally + bass) at a set
// K-weighted level vs the dry sum, an optional echo return, optionally a 2 s stop (a "break" at 8 s),
// 12 s of music (verse / chorus / outro, 4 s each) and a 2 s tail at the end.
struct SpaceScene {
    bool padWide = true;
    bool padAntiPhase = false;    // over-widened pad: R mostly the inverted L
    double padMinusL = 0.0;       // mildly over-widened pad: R = r - padMinusL * l (0.15: correlation ~ -0.15, a fully wet chorus + width)
    bool withPad = true;
    double padDb = 2.0;           // pad level vs the lead (K-weighted, while the lead plays: roughly)
    double hallLu = -9.0;         // hall return vs the dry sum, LU (K-weighted; vs the whole mix it reads lower); <= -90: none
    double rt60 = 2.5;
    bool bassToHall = false;      // low-end reverb
    double echoLu = -99.0;        // echo return vs the dry sum (<= -90: none)
    bool echoThrows = false;      // the echo only gets the last 8th note of every 4 s phrase (an automated throw)
    bool echoIntoHall = false;    // the echo return's output feeds the hall (a bus output into a return)
    std::string hallFx = "reverb";  // the effect on the "hall" return (shimmer = a reverb, dimension = a width return)
    double shimmerLu = -99.0;     // a second reverb return ("shimmer") fed by the pad in the verse (0-4 s) only, LU vs the
                                  // dry sum there (an automated send: it blooms in one section); <= -90: none
    bool stop = false;           // everything stops for 2 s at 16 s (a break)
    bool routing = true;
    bool group = false;           // pad and lead through a "music" group bus
    double masterGainDb = 0.0;    // gain after the sum (a master limiter's input gain)
    std::string profile = "synthwave";
};

json spaceReport(const SpaceScene& sc, as::MixAnalyzer* keep = nullptr) {
    const double sr = 48000.0, beat = 0.5;
    const double musicEnd = sc.stop ? 14.0 : 12.0, total = musicEnd + 2.0;
    const auto n = static_cast<std::size_t>(total * sr);
    Stereo kick = silence(sr, total), bass = kick, pad = kick, lead = kick;
    std::vector<float> padIn(n, 0.0f), leadIn(n, 0.0f), bassIn(n, 0.0f);
    const double chord[3] = {220.0, 277.18, 329.63};
    const double mel[4] = {880.0, 987.77, 1174.66, 987.77};
    for (std::size_t i = 0; i < n; ++i) {
        const double t = static_cast<double>(i) / sr;
        if (t >= musicEnd || (sc.stop && t >= 8.0 && t < 10.0)) continue;
        const double inBeat = std::fmod(t, beat);
        kick.L[i] = kick.R[i] = static_cast<float>(0.5 * std::exp(-inBeat / 0.1) * std::sin(2 * kPi * (50.0 * inBeat + 30.0 * 0.03 *
                                                                                                          (1.0 - std::exp(-inBeat / 0.03)))));
        bass.L[i] = bass.R[i] = bassIn[i] = static_cast<float>(0.2 * std::sin(2 * kPi * 55.0 * t));
        if (sc.withPad) {
            double l = 0.0, r = 0.0;
            for (int v = 0; v < 3; ++v)
                for (int h = 1; h <= 4; ++h) {
                    const double f = chord[v] * h;
                    l += std::sin(2 * kPi * f * t * (sc.padWide ? 0.997 : 1.0) + v) / h;
                    r += std::sin(2 * kPi * f * t * (sc.padWide ? 1.003 : 1.0) + v + (sc.padWide ? 1.7 * h : 0.0)) / h;
                }
            pad.L[i] = static_cast<float>(0.03 * l);
            pad.R[i] = static_cast<float>(sc.padAntiPhase ? 0.03 * (0.4 * r - 0.8 * l) : 0.03 * (r - sc.padMinusL * l));
            padIn[i] = 0.5f * (pad.L[i] + pad.R[i]);
        }
        const double inNote = std::fmod(t, 0.25);  // 8th notes, 0.2 s each
        if (inNote < 0.2) {
            const double f = mel[static_cast<std::size_t>(t / 0.25) % 4];
            double sq = 0.0;
            for (int h = 1; h <= 9; h += 2) sq += std::sin(2 * kPi * f * h * t) / h;
            lead.L[i] = lead.R[i] = leadIn[i] = static_cast<float>(0.06 * sq * std::min(1.0, inNote / 0.005) * std::min(1.0, (0.2 - inNote) / 0.005));
        }
    }
    // Pad level vs the lead (K-weighted over the whole song).
    if (sc.withPad) scale(pad, std::sqrt(std::pow(10.0, sc.padDb / 10.0) * kEnergy(lead, sr) / std::max(1e-12, kEnergy(pad, sr))));
    for (std::size_t i = 0; i < n; ++i) padIn[i] = 0.5f * (pad.L[i] + pad.R[i]);
    const Stereo dry = sum({&kick, &bass, &pad, &lead}, n);
    const double dryK = kEnergy(dry, sr, 0, static_cast<std::size_t>(musicEnd * sr));
    std::vector<float> hallIn(n);
    for (std::size_t i = 0; i < n; ++i) hallIn[i] = padIn[i] + leadIn[i] + (sc.bassToHall ? 4.0f * bassIn[i] : 0.0f);
    Stereo hall = schroeder(hallIn, sr, sc.rt60);
    const bool withHall = sc.hallLu > -90.0;
    if (withHall) scale(hall, std::sqrt(std::pow(10.0, sc.hallLu / 10.0) * dryK / std::max(1e-12, kEnergy(hall, sr, 0, static_cast<std::size_t>(musicEnd * sr)))));
    Stereo echo = silence(sr, total);
    const bool withEcho = sc.echoLu > -90.0;
    if (withEcho) {
        const std::size_t d = static_cast<std::size_t>(0.375 * sr);
        for (std::size_t i = d; i < n; ++i) {
            const bool thrown = !sc.echoThrows || std::fmod(static_cast<double>(i - d) / sr, 4.0) >= 3.75;
            echo.L[i] = (thrown ? leadIn[i - d] : 0.0f) + 0.3f * echo.L[i - d];
            echo.R[i] = 0.8f * echo.L[i];
        }
        scale(echo, std::sqrt(std::pow(10.0, sc.echoLu / 10.0) * dryK / std::max(1e-12, kEnergy(echo, sr, 0, static_cast<std::size_t>(musicEnd * sr)))));
    }
    const bool withShim = sc.shimmerLu > -90.0;
    Stereo shim = silence(sr, total);
    if (withShim) {
        const auto verseEnd = static_cast<std::size_t>(4.0 * sr);
        std::vector<float> shimIn(n, 0.0f);
        for (std::size_t i = 0; i < verseEnd; ++i) shimIn[i] = padIn[i];
        shim = schroeder(shimIn, sr, 1.5);
        scale(shim, std::sqrt(std::pow(10.0, sc.shimmerLu / 10.0) * kEnergy(dry, sr, 0, verseEnd) /
                              std::max(1e-12, kEnergy(shim, sr, 0, verseEnd))));
    }
    std::vector<const Stereo*> parts = {&kick, &bass, &pad, &lead};
    if (withHall) parts.push_back(&hall);
    if (withShim) parts.push_back(&shim);
    if (withEcho) parts.push_back(&echo);
    Stereo mix = sum(parts, n);
    scale(mix, std::pow(10.0, sc.masterGainDb / 20.0));
    const Stereo music = sum({&pad, &lead}, n);

    std::vector<Stereo> nodes = {kick, bass};
    std::vector<std::string> ids = {"kick", "bass"};
    std::vector<bool> buses = {false, false};
    if (sc.withPad) { nodes.push_back(pad); ids.push_back("pad"); buses.push_back(false); }
    nodes.push_back(lead); ids.push_back("lead"); buses.push_back(false);
    if (withHall) { nodes.push_back(hall); ids.push_back("hall"); buses.push_back(true); }
    if (withEcho) { nodes.push_back(echo); ids.push_back("echo"); buses.push_back(true); }
    if (withShim) { nodes.push_back(shim); ids.push_back("shimmer"); buses.push_back(true); }
    if (sc.group) { nodes.push_back(music); ids.push_back("music"); buses.push_back(true); }

    std::vector<as::SectionMarker> sections = {{"verse", 0.0, 4.0}, {"chorus", 4.0, 8.0}};
    if (sc.stop) sections.push_back({"break", 8.0, 10.0});
    sections.push_back({"outro", sc.stop ? 10.0 : 8.0, musicEnd});
    // Routing as the renderer would describe it (send levels are only used to phrase the fixes).
    auto routingOf = [&](const std::string& id) {
        as::NodeRouting r;
        const std::string out = sc.group && (id == "pad" || id == "lead") ? "music" : "master";
        r.output = out;
        auto notes = [&](double every, double len) {
            for (double b = 0.0; b < musicEnd / beat; b += every) r.notes.emplace_back(b, len);
        };
        if (id == "kick") { r.instrument = "drums"; notes(1.0, 0.25); }
        if (id == "bass") { r.instrument = "va"; notes(4.0, 4.0); }
        if (id == "pad") {
            r.instrument = "va";
            for (double b = 0.0; b < musicEnd / beat; b += 4.0)
                for (int v = 0; v < 3; ++v) r.notes.emplace_back(b, 4.0);
            r.sends = {{"hall", -6.0}};
            if (sc.shimmerLu > -90.0) r.sends.push_back({"shimmer", -8.0});
            if (sc.padWide) r.fx.push_back({"chorus", json{{"mode", "II"}, {"mix", sc.padMinusL > 0.0 ? 1.0 : 0.5}}});
            if (sc.padMinusL > 0.0) r.fx.push_back({"width", json{{"width", 1.2}}});
        }
        if (id == "lead") {
            r.instrument = "va";
            notes(0.5, 0.4);
            r.sends = {{"hall", -10.0}, {"echo", -12.0}};
        }
        if (id == "hall") r.fx.push_back({sc.hallFx, sc.hallFx == "reverb" ? json{{"type", "hall"}, {"mix", 1.0}} : json{{"mix", 1.0}}});
        if (id == "shimmer") r.fx.push_back({"shimmer", json{{"mix", 1.0}}});
        if (id == "echo") {
            r.fx.push_back({"delay", json{{"mix", 1.0}}});
            if (sc.echoIntoHall) r.output = "hall";
        }
        return r;
    };
    as::MixAnalyzer local;
    as::MixAnalyzer& an = keep ? *keep : local;
    return analyse(an, sr, mix, nodes, ids, sections, 120.0, buses, [&](as::MixAnalyzer& a) { a.setProfile(sc.profile); },
                   [&](as::MixAnalyzer& a, const std::vector<int>& idx) {
                       if (!sc.routing) return;
                       for (std::size_t k = 0; k < idx.size(); ++k) a.setNodeRouting(idx[k], routingOf(ids[k]));
                   });
}

json spaceReportRouted(const SpaceScene& sc) { return spaceReport(sc); }

void testSpace(const std::string& outDir) {
    namespace an = as::analysis;
    auto space = [](const json& r) { return r["space"]; };
    auto hasIssue = [](const json& s, const std::string& i) {
        for (const auto& x : s["issues"]) if (x == i) return true;
        return false;
    };

    // Dry and narrow: centred pad, hall 22 LU under the mix.
    SpaceScene dryNarrow;
    dryNarrow.padWide = false;
    dryNarrow.hallLu = -22.0;
    const json r1 = spaceReportRouted(dryNarrow);
    const json s1 = space(r1);
    check(hasWarning(r1, "dry_mix", {"hall"}) && hasWarning(r1, "narrow_mix", {"pad"}) && s1["verdict"] == "dry",
          "dry + narrow scene: dry_mix names the hall, narrow_mix names the centred pad, verdict dry (" + s1["verdict"].dump() + ", " +
              s1["issues"].dump() + ")");
    check(std::fabs(s1["wetnessLu"].get<double>() + 22.0) < 1.5, fmt("wetness measured %.1f LU (set -22)", s1["wetnessLu"].get<double>()));
    check(s1["widthAbove150HzPct"].get<double>() < 15.0 && s1["musicWidthPct"].get<double>() < 5.0,
          fmt("centred pad: width above 150 Hz %.1f %%, music %.1f %%", s1["widthAbove150HzPct"].get<double>(), s1["musicWidthPct"].get<double>()));
    bool sendFix = false;
    for (const auto& sg : r1["suggestions"]) {
        const std::string t = sg.get<std::string>();
        sendFix = sendFix || (t.find("'pad' -> 'hall' -6 -> ") != std::string::npos && t.find("'lead' -> 'hall'") != std::string::npos);
    }
    check(sendFix, "dry_mix suggestion raises the actual sends ('pad' -> 'hall' -6 -> ...)");
    check(s1["roles"]["kick"] == "drums" && s1["roles"]["bass"] == "bass" && s1["roles"]["pad"] == "bed" && s1["roles"]["lead"] == "lead" &&
              s1["roles"]["hall"] == "return:reverb" && r1["nodes"][4]["role"] == "return" && r1["nodes"][4]["returnKind"] == "reverb",
          "roles: kick drums, bass bass, pad bed (whole notes), lead lead, hall return:reverb " + s1["roles"].dump());
    check(s1["reference"].get<std::string>().find("pre-master") == 0, "with routing the returns are measured against the pre-master sum");

    // Lush: wide pad, hall 9 LU under the mix, pad and lead through a group bus.
    SpaceScene lush;
    lush.group = true;
    const json r2 = spaceReportRouted(lush);
    const json s2 = space(r2);
    const bool noSpaceWarn = !hasWarning(r2, "dry_mix") && !hasWarning(r2, "narrow_mix") && !hasWarning(r2, "washy") &&
                             !hasWarning(r2, "thin_bed") && !hasWarning(r2, "reverb_inaudible") && !hasWarning(r2, "over_wide");
    check(noSpaceWarn && s2["verdict"] == "lush",
          "lush scene (wide pad, hall -9 LU, group bus): no space warning, verdict lush (" + s2["verdict"].dump() + " " + s2["issues"].dump() +
              ", width>150 " + s2["widthAbove150HzPct"].dump() + ", wet " + s2["wetnessLu"].dump() + ", bed " + s2["bedVsLeadDb"].dump() + ")");
    check(s2["roles"]["music"] == "group" && std::fabs(s2["wetnessLu"].get<double>() + 9.0) < 1.5,
          "group bus recognised (outputs feed it), wetness vs the pre-master sum " + s2["wetnessLu"].dump());
    // A master gain does not change the wet/dry balance when the routing is known ...
    SpaceScene loud = lush;
    loud.masterGainDb = 6.0;
    const json s3 = space(spaceReportRouted(loud));
    check(std::fabs(s3["wetnessLu"].get<double>() - s2["wetnessLu"].get<double>()) < 0.05,
          "master gain +6 dB: wetness unchanged with routing (" + s3["wetnessLu"].dump() + ")");
    // ... without routing the returns are found by name and compared with the final mix.
    SpaceScene named = lush;
    named.routing = false;
    named.group = false;
    named.masterGainDb = 6.0;
    const json r4 = spaceReportRouted(named);
    const json s4 = space(r4);
    check(s4["roles"]["hall"] == "return:reverb" && s4["roles"]["pad"] == "bed" && s4["reference"].get<std::string>().find("final mix") != std::string::npos &&
              std::fabs(s4["wetnessLu"].get<double>() - (s2["wetnessLu"].get<double>() - 6.0)) < 1.0,
          "no routing: hall found by name, pad a bed by its steady envelope, wetness vs the final mix " + s4["wetnessLu"].dump());

    // Washy: the hall as loud as the dry sum (3 LU under the whole mix); low-end reverb: the bass in the hall.
    SpaceScene washy;
    washy.hallLu = 0.0;
    const json r5 = spaceReportRouted(washy);
    check(hasWarning(r5, "washy", {"hall"}) && space(r5)["verdict"] == "washy",
          "hall 3 LU under the mix: 'washy', verdict washy (" + space(r5)["verdict"].dump() + " " + space(r5)["issues"].dump() + ", wet " +
              space(r5)["wetnessLu"].dump() + ")");
    SpaceScene lowWash;
    lowWash.bassToHall = true;
    lowWash.hallLu = -8.0;
    const json r6 = spaceReportRouted(lowWash);
    bool lowMsg = false;
    for (const auto& w : r6["warnings"]) lowMsg = lowMsg || (w["code"] == "washy" && w["message"].get<std::string>().find("below 150 Hz") != std::string::npos);
    check(lowMsg && space(r6)["returnLowPct"].get<double>() > 30.0, "bass in the hall: low-end reverb flagged 'washy' (" +
                                                                         space(r6)["returnLowPct"].dump() + " % below 150 Hz)");

    // Overshoot of a width fix: a pad widened into anti-phase.
    SpaceScene overWide = lush;
    overWide.padAntiPhase = true;
    const json rOw = spaceReportRouted(overWide);
    check(hasWarning(rOw, "over_wide", {"pad"}) && hasIssue(space(rOw), "over_wide") && space(rOw)["verdict"] != "lush",
          "anti-phase pad: over_wide names it, verdict no longer lush (" + space(rOw)["verdict"].dump() + ")");
    // The typical overshoot: a fully wet chorus + width boost leaves the pad at correlation ~ -0.15.
    SpaceScene wetChorus = lush;
    wetChorus.padMinusL = 0.15;
    const json rWc = spaceReportRouted(wetChorus);
    bool chorusFix = false;
    for (const auto& sg : rWc["suggestions"]) chorusFix = chorusFix || sg.get<std::string>().find("'pad' chorus mix 1 -> 0.5") != std::string::npos;
    double padCorr = 1.0;
    for (const auto& nd : rWc["nodes"]) if (nd["id"] == "pad") padCorr = nd["correlation"].get<double>();
    check(hasWarning(rWc, "over_wide", {"pad"}) && chorusFix && space(rWc)["verdict"] == "ok" && padCorr < -0.1 && padCorr > -0.25,
          "pad at correlation " + std::to_string(padCorr) + " (fully wet chorus + width): over_wide, fix 'chorus mix 1 -> 0.5', verdict ok (" +
              space(rWc)["verdict"].dump() + ")");
    double lushPadCorr = -1.0;
    for (const auto& nd : r2["nodes"]) if (nd["id"] == "pad") lushPadCorr = nd["correlation"].get<double>();
    check(lushPadCorr > -0.1, fmt("the lush scene's wide pad (correlation %.2f) is not over-wide", lushPadCorr));

    // Thin bed (synthwave), missing bed, and no bed check under the default profile.
    SpaceScene thin;
    thin.padDb = -12.0;
    const json r7 = spaceReportRouted(thin);
    check(hasWarning(r7, "thin_bed", {"pad", "lead"}) && space(r7)["bedVsLeadDb"].get<double>() < -8.0,
          "pad 12 dB under the lead: thin_bed names pad and lead (bed " + space(r7)["bedVsLeadDb"].dump() + " dB)");
    SpaceScene noBed;
    noBed.withPad = false;
    const json r8 = spaceReportRouted(noBed);
    bool missing = false;
    for (const auto& w : r8["warnings"]) missing = missing || (w["code"] == "thin_bed" && w["message"].get<std::string>().find("missing") != std::string::npos);
    check(missing, "no pad at all: thin_bed says the bed is missing");
    SpaceScene thinDefault = thin;
    thinDefault.profile = "default";
    check(!hasWarning(spaceReportRouted(thinDefault), "thin_bed"), "default profile: the bed is not judged");

    // Echo too quiet, and reverb tails at a stop: short vs long decay.
    SpaceScene quietEcho = lush;
    quietEcho.echoLu = -34.0;
    const json r9 = spaceReportRouted(quietEcho);
    check(hasWarning(r9, "reverb_inaudible", {"echo"}), "echo return 34 LU under the mix: reverb_inaudible names it");
    // Echo throws (only the last note of each phrase): sparse, so low on average, but loud when they happen.
    SpaceScene throws = lush;
    throws.echoLu = -31.0;
    throws.echoThrows = true;
    const json rTh = spaceReportRouted(throws);
    double thAvg = 0.0, thActive = -99.0;
    const json sTh = space(rTh);
    for (const auto& rt : sTh["returns"])
        if (rt["id"] == "echo") { thAvg = rt["lu"].get<double>(); thActive = rt.value("activeLu", -99.0); }
    check(!hasWarning(rTh, "reverb_inaudible") && thAvg < -24.0 && thActive > -24.0,
          fmt("echo throws: %.1f LU on average but %.1f LU while they sound -> audible, no reverb_inaudible", thAvg, thActive) +
              (thActive > -24.0 ? std::string() : " " + sTh["returns"].dump()));
    SpaceScene quietThrows = throws;
    quietThrows.echoLu = -42.0;
    check(hasWarning(spaceReportRouted(quietThrows), "reverb_inaudible", {"echo"}), "echo throws 11 dB quieter: reverb_inaudible");
    // An echo return whose output feeds the hall (a bus output into a return) keeps the hall a reverb return.
    SpaceScene chain = lush;
    chain.echoLu = -18.0;
    chain.echoIntoHall = true;
    const json rCh = spaceReportRouted(chain);
    check(space(rCh)["roles"]["hall"] == "return:reverb" && space(rCh)["roles"]["echo"] == "return:delay" && !hasIssue(space(rCh), "no_reverb") &&
              !hasWarning(rCh, "dry_mix"),
          "echo -> hall: hall stays a reverb return (" + space(rCh)["roles"].dump() + ")");
    // Returns classified by their effects: a shimmer return is a reverb, a dimension / microshift return a width return.
    SpaceScene shimmerHall = lush;
    shimmerHall.hallFx = "shimmer";
    SpaceScene dimHall = lush;
    dimHall.hallFx = "dimension";
    check(space(spaceReportRouted(shimmerHall))["roles"]["hall"] == "return:reverb" &&
              space(spaceReportRouted(dimHall))["roles"]["hall"] == "return:width",
          "a shimmer return counts as reverb, a dimension return as width (" + space(spaceReportRouted(dimHall))["roles"].dump() + ")");
    // A second reverb that blooms in one section only (automated send) is quiet on average but heard there.
    SpaceScene bloom = lush;
    bloom.shimmerLu = -20.5;
    const json rBl = spaceReportRouted(bloom);
    double blAvg = 0.0;
    const json sBl = space(rBl);  // (a named copy: iterating a member of the temporary would dangle)
    for (const auto& rt : sBl["returns"])
        if (rt["id"] == "shimmer") blAvg = rt["lu"].get<double>();
    SpaceScene faint = bloom;
    faint.shimmerLu = -33.0;
    check(blAvg < -24.0 && !hasWarning(rBl, "reverb_inaudible") && hasWarning(spaceReportRouted(faint), "reverb_inaudible", {"shimmer"}),
          fmt("shimmer blooming in the verse only: %.1f LU on average, not flagged; 12.5 dB fainter: flagged", blAvg) + " " +
              sBl["returns"].dump());
    SpaceScene shortTail = lush;
    shortTail.stop = true;
    shortTail.rt60 = 0.15;
    const json r10 = spaceReportRouted(shortTail);
    SpaceScene longTail = shortTail;
    longTail.rt60 = 3.0;
    const json r11 = spaceReportRouted(longTail);
    const double shortDb = space(r10)["tails"]["tailDb"], longDb = space(r11)["tails"]["tailDb"];
    bool tailMsg = false;
    for (const auto& w : r10["warnings"]) tailMsg = tailMsg || (w["code"] == "reverb_inaudible" && w["message"].get<std::string>().find("stops") != std::string::npos);
    check(tailMsg && space(r10)["tails"]["count"].get<int>() >= 2 && shortDb < -30.0 && longDb > -30.0 && !hasWarning(r11, "reverb_inaudible"),
          fmt("tails at the stop and the end: RT60 0.15 s -> %.1f dB (flagged), 3 s -> %.1f dB (fine)", shortDb, longDb));

    // No reverb return at all.
    SpaceScene none = lush;
    none.hallLu = -99.0;
    const json r12 = spaceReportRouted(none);
    check(hasWarning(r12, "dry_mix") && hasIssue(space(r12), "no_reverb"), "no reverb return: dry_mix, issue no_reverb");

    // Deterministic, never null, in the summary; images of the dry and the lush scene (overview SPACE
    // strip, stereo.png width target / wetness panel / space strip) are written for a look.
    check(spaceReportRouted(dryNarrow) == r1, "space assessment is deterministic");
    check(r1.dump().find("null") == std::string::npos && r12.dump().find("null") == std::string::npos, "space report has no null values");
    check(r1["summary"].get<std::string>().find("space dry") != std::string::npos, "summary line carries the space verdict");
    bool images = true;
    for (const auto& [name, sc] : {std::pair<std::string, SpaceScene>{"space_dry", dryNarrow}, {"space_lush", lush}, {"space_tails", shortTail}}) {
        as::MixAnalyzer a;
        spaceReport(sc, &a);
        fs::create_directories(outDir + "/" + name);
        a.writeImages(outDir + "/" + name);
        images = images && fs::exists(outDir + "/" + name + "/stereo.png") && fs::exists(outDir + "/" + name + "/overview.png");
    }
    check(images, "space scenes: overview.png and stereo.png written (" + outDir + "/space_*)");
    check(std::string(an::roleName(an::Role::Bed)) == "bed" && std::string(an::returnKindName(an::ReturnKind::Delay)) == "delay",
          "role / return kind names");
}

// Role names: whole-word matches only where a substring would mislead, and the routing the renderer
// hands over (setRouting from the parsed song) with an automated (throw-only) send.
void testSpaceNamesAndSongRouting() {
    const double sr = 48000.0, secs = 8.0;
    const std::vector<std::string> ids = {"heartbeat_pad", "offbeat_stab", "sunrise_lead", "crossing_keys", "breakdown_strings",
                                          "window_pad", "bigkick", "sub_808", "bass_drum"};
    std::vector<Stereo> nodes;
    for (std::size_t k = 0; k < ids.size(); ++k) nodes.push_back(sine(sr, secs, 300.0 + 97.0 * static_cast<double>(k), -30.0));
    Stereo mix = silence(sr, secs);
    for (const auto& s : nodes)
        for (std::size_t i = 0; i < mix.size(); ++i) { mix.L[i] += s.L[i]; mix.R[i] += s.R[i]; }
    as::MixAnalyzer an;
    const json r = analyse(an, sr, mix, nodes, ids);
    const json roles = r["space"]["roles"];
    check(roles["heartbeat_pad"] == "bed" && roles["offbeat_stab"] != "drums" && roles["sunrise_lead"] == "lead" &&
              roles["crossing_keys"] != "lead" && roles["breakdown_strings"] == "bed" && roles["window_pad"] == "bed" &&
              roles["bigkick"] == "drums" && roles["sub_808"] == "bass" && roles["bass_drum"] == "drums",
          "role names: no substring traps (heartbeat/offbeat/sunrise/crossing/breakdown/window), 808 bass vs bass drum " + roles.dump());

    // A pad whose hall send is only automated (static -120 dB, raised to -4 dB): it feeds the hall, and a
    // dry_mix plan phrases the automated level, not -120.
    as::SongSpec song;
    as::NodeSpec pad;
    pad.id = "pad";
    pad.kind = as::NodeSpec::Kind::Track;
    pad.instrumentType = "va";
    pad.sends = {{"hall", -120.0f}};
    as::AutomationLane lane;
    lane.target = "send.hall";
    lane.points = {{0.0, -120.0}, {8.0, -4.0}};
    pad.automation.push_back(lane);
    for (double b = 0.0; b < 16.0; b += 4.0)
        for (int v = 0; v < 3; ++v) {
            as::NoteSpec note;
            note.startBeat = b;
            note.durationBeats = 4.0;
            pad.notes.push_back(note);
        }
    as::NodeSpec hall;
    hall.id = "hall";
    hall.kind = as::NodeSpec::Kind::Bus;
    as::FxSpec verb;
    verb.type = "reverb";
    verb.params = json{{"mix", 1.0}};
    hall.fx.push_back(verb);
    song.nodes = {pad, hall};
    Stereo padA = sine(sr, secs, 440.0, -20.0, true, true, 1.0);
    std::vector<float> in(padA.size());
    for (std::size_t i = 0; i < in.size(); ++i) in[i] = 0.5f * (padA.L[i] + padA.R[i]);
    Stereo hallA = schroeder(in, sr, 2.0);
    scale(hallA, std::sqrt(std::pow(10.0, -24.0 / 10.0) * kEnergy(padA, sr) / std::max(1e-12, kEnergy(hallA, sr))));
    Stereo mix2 = sum({&padA, &hallA}, padA.size());
    as::MixAnalyzer an2;
    const json r2 = analyse(an2, sr, mix2, {padA, hallA}, {"pad", "hall"}, {}, 120.0, {false, true},
                            [](as::MixAnalyzer& a) { a.setProfile("synthwave"); },
                            [&](as::MixAnalyzer& a, const std::vector<int>&) { a.setRouting(song); });
    bool plan = false, unsentClaim = false;
    for (const auto& sg : r2["suggestions"]) {
        const std::string t = sg.get<std::string>();
        plan = plan || t.find("'pad' -> 'hall' -4 -> ") != std::string::npos;
        unsentClaim = unsentClaim || t.find("send nothing to a reverb") != std::string::npos || t.find("sends nothing to a reverb") != std::string::npos;
    }
    const bool routed = r2["space"]["roles"]["hall"] == "return:reverb" && r2["space"]["roles"]["pad"] == "bed" && hasWarning(r2, "dry_mix") &&
                        plan && !unsentClaim;
    check(routed, "setRouting: automated send counts with its loudest level (plan 'pad' -> 'hall' -4 -> ..., pad not called unsent)" +
                      (routed ? std::string() : " " + r2["space"]["roles"].dump() + " " + r2["suggestions"].dump()));
}

// ------------------------------------------------------------------ genre profiles (jazz, classical, pop, rock, film)

// A noise-like multisine with a profile's reference long-term spectrum: 24 log-spaced partials per octave from
// 20 Hz to 20 kHz (each on a multiple of 1/period, so the buffer tiles seamlessly), each carrying the reference
// energy of its 1/24-octave slot (plus tweakDb of its band), with seeded random phases; only the partials in
// [lo, hi) Hz sound. Another seed gives an uncorrelated signal with the same spectrum; full band RMS ~0.1.
const std::vector<float>& profileNoise(const as::analysis::AnalysisProfile& p, double sr, std::size_t period, std::uint64_t seed,
                                       double lo, double hi, const std::array<double, as::analysis::kNumBands>& tweakDb) {
    namespace an = as::analysis;
    static std::map<std::string, std::vector<float>> cache;  // the scenes share their spectra
    std::string key = p.name + fmt("|%g|%g|%g", sr, static_cast<double>(period), static_cast<double>(seed)) + fmt("|%g|%g", lo, hi);
    for (double t : tweakDb) key += fmt("|%g", t);
    if (const auto it = cache.find(key); it != cache.end()) return it->second;
    const double df = sr / static_cast<double>(period);
    const double norm = 0.1 / std::sqrt(p.energy(20.0, 20000.0));
    std::vector<double> acc(period, 0.0);
    as::dsp::Rng rng(seed);
    double lastBin = 0.0;
    for (int i = 0;; ++i) {
        const double f = 20.0 * std::exp2(i / 24.0);
        if (f >= 20000.0) break;
        const double phase = 2.0 * kPi * rng.uniform();  // drawn for every partial: the phases do not depend on lo/hi
        const double bin = std::round(f / df);
        if (bin <= lastBin) continue;
        lastBin = bin;
        if (f < lo || f >= hi) continue;
        int b = 0;
        while (b + 1 < an::kNumBands && f >= an::kBandEdgesHz[b + 1]) ++b;
        const double e = p.energy(f * std::exp2(-1.0 / 48.0), f * std::exp2(1.0 / 48.0)) *
                         std::pow(10.0, tweakDb[static_cast<std::size_t>(b)] / 10.0);
        const double w = 2.0 * kPi * bin / static_cast<double>(period);
        const std::complex<double> rot(std::cos(w), std::sin(w));
        std::complex<double> z = std::polar(norm * std::sqrt(2.0 * e), phase);
        for (std::size_t n = 0; n < period; ++n) {
            acc[n] += z.imag();
            z *= rot;
        }
    }
    return cache[key] = std::vector<float>(acc.begin(), acc.end());
}

// BS.1770 gated integrated loudness of a stereo signal (400 ms blocks, 100 ms hop).
double integratedLufs(const Stereo& s, double sr) {
    as::analysis::KWeighting kl(sr), kr(sr);
    const auto hop = static_cast<std::size_t>(sr / 10.0);
    std::vector<double> ticks;
    double acc = 0.0;
    for (std::size_t i = 0; i < s.size(); ++i) {
        const double l = kl.process(s.L[i]), r = kr.process(s.R[i]);
        acc += l * l + r * r;
        if ((i + 1) % hop == 0) { ticks.push_back(acc); acc = 0.0; }
    }
    std::vector<double> blocks;
    for (std::size_t j = 0; j + 4 <= ticks.size(); ++j)
        blocks.push_back((ticks[j] + ticks[j + 1] + ticks[j + 2] + ticks[j + 3]) / (4.0 * static_cast<double>(hop)));
    return as::analysis::integratedLoudness(blocks);
}

// The master of a loud test mix: a static soft clipper (linear up to 70 % of the ceiling, a tanh knee into
// it). The noise-like test signals have a ~14 dB crest; a gain-riding limiter would have to work all the time
// and flatten the sections (the loudness range) with it, a memoryless clipper only shaves the peaks: the
// sections keep their levels, the PLR shrinks, and the distortion stays ~25 dB down (spectrum unchanged).
void softClipTo(Stereo& s, double ceilingDb) {
    const double c = std::pow(10.0, ceilingDb / 20.0), k = 0.7 * c;
    auto shape = [&](float v) {
        const double a = std::fabs(v);
        if (a <= k) return v;
        return static_cast<float>(std::copysign(k + (c - k) * std::tanh((a - k) / (c - k)), static_cast<double>(v)));
    };
    for (auto& v : s.L) v = shape(v);
    for (auto& v : s.R) v = shape(v);
}

// A genre-shaped test mix: a 'bass' part (partials below 250 Hz, mono) and an 'ensemble' (above 250 Hz,
// stereo: side/mid above 150 Hz = widthPct) following a profile's reference spectrum, sections at set levels
// (the loudness range), a reverb return at a set level vs the dry sum, the music stopping 2.5 s before the
// end (tails), a master gain to the target loudness and optionally a clipper (loud genres' PLR).
struct GenreScene {
    std::string profile;                                    // judged under this profile
    std::string shape;                                      // spectrum of this profile's reference ("" = profile)
    std::array<double, as::analysis::kNumBands> tweakDb{};  // extra dB per band on the dry parts (a wrong balance)
    std::vector<double> sectionDb{-7.0, -2.0, 0.0, -4.0};   // level of each section, sectionSec long each
    double sectionSec = 9.0;
    double widthPct = 30.0;
    double hallLu = -12.0;                                  // reverb return vs the dry sum (K-weighted); <= -90: none
    double rt60 = 1.5;
    bool bassToHall = false;                                // concert halls: the bass is in the reverb too
    double lufs = -14.0;                                    // integrated loudness of the mix
    double ceilingDb = 0.0;                                 // < 0: soft-clip the mix into this sample peak (dBFS)
};

json genreReport(const GenreScene& sc) {
    namespace an = as::analysis;
    const double sr = 48000.0, split = 250.0;
    const std::size_t period = 192000;  // 4 s
    const an::AnalysisProfile& shape = *an::findAnalysisProfile(sc.shape.empty() ? sc.profile : sc.shape);
    const std::vector<float> bassP = profileNoise(shape, sr, period, 11, 0.0, split, sc.tweakDb);
    const std::vector<float> midP = profileNoise(shape, sr, period, 11, split, 1e9, sc.tweakDb);
    const std::vector<float> sideP = profileNoise(shape, sr, period, 29, split, 1e9, sc.tweakDb);
    // Side level for the width above 150 Hz (the bass part's 150-250 Hz counts as mid); the ensemble is scaled
    // down so that mid + side keep the reference energy: w = s2 E / (E + B (1 + s2)).
    const double w = sc.widthPct / 100.0, E = shape.energy(split, 20000.0), B = shape.energy(150.0, split);
    const double s2 = w * (E + B) / (E - w * B);
    const auto side = static_cast<float>(std::sqrt(s2)), ensGain = static_cast<float>(1.0 / std::sqrt(1.0 + s2));
    const std::size_t nSec = sc.sectionDb.size();
    const double musicSec = sc.sectionSec * static_cast<double>(nSec), total = musicSec + 2.5;
    const auto n = static_cast<std::size_t>(total * sr), musicN = static_cast<std::size_t>(musicSec * sr);
    Stereo bass = silence(sr, total), ens = silence(sr, total);
    std::vector<float> hallIn(n, 0.0f);
    std::vector<double> secGain;
    for (double db : sc.sectionDb) secGain.push_back(std::pow(10.0, db / 20.0));
    for (std::size_t i = 0; i < musicN; ++i) {
        const double t = static_cast<double>(i) / sr;
        const std::size_t k = std::min(nSec - 1, static_cast<std::size_t>(t / sc.sectionSec));
        const double into = t - static_cast<double>(k) * sc.sectionSec;
        double gl = secGain[k];
        if (k > 0 && into < 0.05)  // 50 ms ramps between the sections
            gl = std::pow(10.0, (sc.sectionDb[k - 1] + (sc.sectionDb[k] - sc.sectionDb[k - 1]) * into / 0.05) / 20.0);
        const double fade = std::min({1.0, t / 0.02, (musicSec - t) / 0.03});  // no clicks at the start / the stop
        const auto g = static_cast<float>(gl * fade);
        const std::size_t j = i % period;
        const float b = g * bassP[j], m = g * ensGain * midP[j], x = g * ensGain * side * sideP[j];
        bass.L[i] = bass.R[i] = b;
        ens.L[i] = m + x;
        ens.R[i] = m - x;
        hallIn[i] = m + (sc.bassToHall ? b : 0.0f);
    }
    if (sc.bassToHall) {  // the hall's low cut (80 Hz, 12 dB/oct), as on a real hall return
        const double a = 1.0 / (1.0 + 2.0 * kPi * 80.0 / sr);
        for (int pass = 0; pass < 2; ++pass) {
            double x1 = 0.0, y1 = 0.0;
            for (float& v : hallIn) {
                const double y = a * (y1 + v - x1);
                x1 = v;
                y1 = y;
                v = static_cast<float>(y);
            }
        }
    }
    const Stereo dry = sum({&bass, &ens}, n);
    const bool withHall = sc.hallLu > -90.0;
    Stereo hall = withHall ? schroeder(hallIn, sr, sc.rt60) : silence(sr, total);
    if (withHall)
        scale(hall, std::sqrt(std::pow(10.0, sc.hallLu / 10.0) * kEnergy(dry, sr, 0, musicN) /
                              std::max(1e-12, kEnergy(hall, sr, 0, musicN))));
    // Master: gain to the target loudness, then (loud genres) the clipper; the gain is re-trimmed for the
    // loudness the clipper takes away (secant steps: into a clipper 1 dB of gain buys less than 1 dB).
    const Stereo pre = sum({&dry, &hall}, n);
    Stereo mix;
    double gainDb = sc.lufs - integratedLufs(pre, sr), prevGain = 0.0, prevLufs = 0.0;
    for (int it = 0; it < 8; ++it) {
        mix = pre;
        scale(mix, std::pow(10.0, gainDb / 20.0));
        if (sc.ceilingDb >= 0.0) break;
        softClipTo(mix, sc.ceilingDb);
        const double lufs = integratedLufs(mix, sr), err = sc.lufs - lufs;
        if (std::fabs(err) < 0.1) break;
        const double slope = it == 0 ? 1.0 : std::clamp((lufs - prevLufs) / (gainDb - prevGain), 0.1, 1.0);
        prevGain = gainDb;
        prevLufs = lufs;
        gainDb += err / slope;
    }

    std::vector<Stereo> nodes = {bass, ens};
    std::vector<std::string> ids = {"bass", "ensemble"};
    std::vector<bool> buses = {false, false};
    if (withHall) { nodes.push_back(hall); ids.push_back("hall"); buses.push_back(true); }
    std::vector<as::SectionMarker> sections;
    for (std::size_t k = 0; k < nSec; ++k)
        sections.push_back({"part" + std::to_string(k + 1), static_cast<double>(k) * sc.sectionSec, static_cast<double>(k + 1) * sc.sectionSec});
    const double beats = musicSec * 2.0;  // 120 BPM
    auto routingOf = [&](const std::string& id) {
        as::NodeRouting r;
        if (id == "bass") {
            r.instrument = "sampler";
            for (double b = 0.0; b < beats; b += 2.0) r.notes.emplace_back(b, 2.0);
            if (withHall && sc.bassToHall) r.sends = {{"hall", -6.0}};
        }
        if (id == "ensemble") {
            r.instrument = "sampler";
            for (double b = 0.0; b < beats; b += 4.0)
                for (int v = 0; v < 3; ++v) r.notes.emplace_back(b, 4.0);
            if (withHall) r.sends = {{"hall", -6.0}};
        }
        if (id == "hall") r.fx.push_back({"reverb", json{{"type", "hall"}, {"mix", 1.0}}});
        return r;
    };
    as::MixAnalyzer analyzer;
    return analyse(analyzer, sr, mix, nodes, ids, sections, 120.0, buses, [&](as::MixAnalyzer& a) { a.setProfile(sc.profile); },
                   [&](as::MixAnalyzer& a, const std::vector<int>& idx) {
                       for (std::size_t k = 0; k < idx.size(); ++k) a.setNodeRouting(idx[k], routingOf(ids[k]));
                   });
}

// The warnings whose thresholds come from the analysis profile (plus clicks: a test mix must be clean).
std::string profileWarnings(const json& r) {
    static const char* kCodes[] = {"dull", "tilt", "loudness_low", "loudness_high", "lra_low", "lra_high", "squashed", "true_peak",
                                   "dry_mix", "narrow_mix", "washy", "thin_bed", "reverb_inaudible", "over_wide", "clicks"};
    std::string s;
    for (const auto& w : r["warnings"]) {
        const std::string code = w["code"];
        bool hit = code.rfind("balance_", 0) == 0;
        for (const char* c : kCodes) hit = hit || code == c;
        if (hit) s += (s.empty() ? "" : ", ") + code;
    }
    return s;
}

double maxBandDev(const json& r) {
    double m = 0.0;
    for (const auto& [b, v] : r["global"]["bandsVsRefDb"].items()) m = std::max(m, std::fabs(v.get<double>()));
    return m;
}

std::string digest(const json& r) {
    const json& g = r["global"];
    const json& s = r["space"];
    char buf[400];
    std::snprintf(buf, sizeof buf, "%.1f LUFS, LRA %.1f, PLR %.1f, TP %.2f, max band dev %.1f dB, tilt %.2f/%.2f, width>150 %.0f%%, reverb %s LU "
                                   "(%.0f %% < 150 Hz), tails %s dB, verdict %s",
                  g["lufsIntegrated"].get<double>(), g["loudnessRange"].get<double>(), g["plr"].get<double>(), g["truePeakDbtp"].get<double>(),
                  maxBandDev(r), g["spectralTiltDbPerOct"].get<double>(), g["referenceTiltDbPerOct"].get<double>(),
                  s.value("widthAbove150HzPct", -1.0), s.contains("wetnessLu") ? s["wetnessLu"].dump().c_str() : "none",
                  s.value("returnLowPct", 0.0), s["tails"].contains("tailDb") ? s["tails"]["tailDb"].dump().c_str() : "none",
                  s["verdict"].get<std::string>().c_str());
    std::string bands, secs;
    for (const char* b : as::analysis::kBandNames) bands += fmt(" %.1f", g["bandsVsRefDb"][b].get<double>());
    for (const auto& sec : r["sections"]) secs += fmt(" %.1f", sec["lufs"].get<double>());
    return buf + std::string("; bands") + bands + "; sections LUFS" + secs;
}

void testGenreProfiles() {
    namespace an = as::analysis;
    const auto t0 = std::chrono::steady_clock::now();
    auto prof = [](const char* name) { return an::findAnalysisProfile(name); };
    const auto *jz = prof("jazz"), *cl = prof("classical"), *po = prof("pop"), *ro = prof("rock"), *fi = prof("film");
    check(jz && cl && po && ro && fi, "profiles jazz, classical, pop, rock, film exist");
    if (!(jz && cl && po && ro && fi)) return;
    {   // The style facts the references encode (band shares of the reference curves).
        const auto d = an::defaultAnalysisProfile().bandShares(), sw = prof("synthwave")->bandShares();
        const auto j = jz->bandShares(), c = cl->bandShares(), p = po->bandShares(), r = ro->bandShares(), f = fi->bandShares();
        check(j[0] < 0.5 * d[0] && c[0] < 0.5 * d[0] && r[0] < d[0] && d[0] < f[0] && f[0] < p[0] && p[0] < sw[0],
              fmt("sub share: jazz %.1f %% / classical %.1f %% < half the default's; rock < default < film < pop < synthwave "
                  "(pop %.1f %%)", 100 * j[0], 100 * c[0], 100 * p[0]));
        check(c[5] + c[6] < j[5] + j[6] && j[5] + j[6] < d[5] + d[6] && d[5] + d[6] < p[5] + p[6] && f[5] + f[6] < d[5] + d[6],
              "top (6-20 kHz): classical < jazz < default < pop; film darker than default");
        check(r[2] + r[3] > d[2] + d[3] + 0.05 && j[2] + j[3] > d[2] + d[3] && p[2] < d[2],
              fmt("mids: rock %.0f %% and jazz forward vs default %.0f %%; pop's low mids cleaner", 100 * (r[2] + r[3]), 100 * (d[2] + d[3])));
        check(jz->lufsMin == -16 && jz->lufsMax == -13 && cl->lufsMin == -23 && cl->lufsMax == -16 && po->lufsMin == -11 && po->lufsMax == -8 &&
                  ro->lufsMin == -10 && ro->lufsMax == -7 && fi->lufsMin == -16 && fi->lufsMax == -10,
              "loudness targets: jazz -16..-13, classical -23..-16, pop -11..-8, rock -10..-7, film -16..-10");
        check(cl->plrMinDb >= 12 && cl->lraMaxLu >= 20 && jz->plrMinDb >= 9 && jz->lraMinLu >= 5 && jz->lraMaxLu <= 14 && ro->plrMinDb <= 5 &&
                  po->lraMaxLu <= 12 && cl->wetMaxLu > jz->wetMaxLu && cl->returnLowMaxPct > 30.0 && !cl->bedBelowLeadMaxDb &&
                  !cl->bandLowDb[0] && !jz->bandLowDb[0],
              "dynamics / space: classical PLR >= 12 and LRA up to 20+, jazz PLR >= 9 and LRA 5-14, rock PLR >= 5, pop LRA <= 12, the hall "
              "wetter than the jazz room, no sub demand in jazz / classical");
    }

    // Genre reference mixes: judged under their own profile, no profile-dependent warning fires; the same mix
    // under 'default' (the pop / synthwave master reference) is flagged where the genres differ.
    GenreScene jazz;
    jazz.profile = "jazz";
    jazz.sectionDb = {-7.0, -2.0, 0.0, -4.0};  // intro, head, solo, out
    jazz.widthPct = 30.0;
    jazz.hallLu = -14.0;
    jazz.rt60 = 1.1;
    jazz.lufs = -14.5;
    jazz.ceilingDb = -3.0;
    GenreScene classical;
    classical.profile = "classical";
    classical.sectionDb = {-17.0, -7.0, 0.0, -3.0, -14.0};  // pp intro, theme, tutti, tutti, coda
    classical.sectionSec = 8.0;
    classical.widthPct = 45.0;
    classical.hallLu = -8.0;
    classical.rt60 = 2.2;
    classical.bassToHall = true;
    classical.lufs = -19.5;
    GenreScene piano;  // a solo piano in a hall (the Gymnopedie etude's reference recordings)
    piano.profile = "piano";
    piano.sectionDb = {-10.0, -4.0, 0.0, -6.0, -12.0};
    piano.sectionSec = 8.0;
    piano.widthPct = 30.0;
    piano.hallLu = -9.0;
    piano.rt60 = 1.8;
    piano.lufs = -20.0;
    GenreScene pop;
    pop.profile = "pop";
    pop.sectionDb = {-6.0, -3.0, 0.0, -2.0};  // verse, pre-chorus, chorus, bridge
    pop.widthPct = 55.0;
    pop.hallLu = -12.0;
    pop.rt60 = 1.8;
    pop.lufs = -9.8;
    pop.ceilingDb = -2.0;
    GenreScene rock;
    rock.profile = "rock";
    rock.sectionDb = {-5.0, -1.0, 0.0, -3.0};  // verse, chorus, solo, bridge
    rock.widthPct = 45.0;
    rock.hallLu = -15.0;
    rock.rt60 = 1.4;
    rock.lufs = -8.5;
    rock.ceilingDb = -1.8;
    GenreScene film;
    film.profile = "film";
    film.sectionDb = {-12.0, -5.0, 0.0, -2.0, -10.0};
    film.sectionSec = 8.0;
    film.widthPct = 60.0;
    film.hallLu = -7.0;
    film.rt60 = 2.5;  // low hits and synth sub stay out of the hall
    film.lufs = -13.0;
    film.ceilingDb = -2.0;

    struct RefCase { GenreScene sc; std::vector<const char*> underDefault; };
    const RefCase refs[] = {{jazz, {"loudness_low"}}, {classical, {"loudness_low", "lra_high"}}, {piano, {"loudness_low"}}, {pop, {}},
                            {rock, {"loudness_high"}}, {film, {"loudness_low"}}};
    for (const auto& [sc, underDefault] : refs) {
        const json r = genreReport(sc);
        const std::string warns = profileWarnings(r);
        check(warns.empty() && maxBandDev(r) < 1.5 && r["reference"]["profile"] == sc.profile &&
                  (r["space"]["verdict"] == "lush" || r["space"]["verdict"] == "ok"),
              "'" + sc.profile + "' reference mix under its profile: no profile warning (" + (warns.empty() ? "none" : warns) + "); " + digest(r));
        if (sc.profile == "classical") {  // the report states the thresholds it used
            const json& ref = r["reference"];
            const json& tg = r["space"]["targets"];
            check(ref["lufsTarget"] == json::array({-23.0, -16.0}) && ref["bandLimitsDb"]["sub"] == json{{"high", 7.0}} &&
                      ref["plrMinDb"] == 12.0 && ref["lraRangeLu"] == json::array({4.0, 22.0}) && tg["profile"] == "classical" &&
                      tg["wetnessLu"] == json::array({-14.0, -4.0}) && tg["returnLowMaxPct"] == 50.0 && !tg.contains("bedBelowLeadMaxDb"),
                  "report.reference / space.targets state the classical thresholds (sub not checked low, PLR 12, LRA 4-22, hall -14..-4 LU)");
        }
        if (sc.profile == "piano") {  // a real solo piano's balance is not an orchestra's: 'classical' flags it
            GenreScene o = sc;
            o.profile = "classical";
            o.shape = "piano";
            const json ro = genreReport(o);
            check(hasWarning(ro, "balance_lowmid_high") && hasWarning(ro, "balance_mid_high"),
                  "the 'piano' reference mix under 'classical' reads the piano's hump as muddy / boxy (" + profileWarnings(ro) + ")");
        }
        if (underDefault.empty()) continue;
        GenreScene d = sc;
        d.profile = "default";
        const json rd = genreReport(d);
        bool all = true;
        for (const char* code : underDefault) all = all && hasWarning(rd, code);
        check(all, "the '" + sc.profile + "' reference mix under 'default' is flagged (" + profileWarnings(rd) + ")");
    }

    // Clearly wrong mixes are flagged under the genre's profile.
    struct WrongCase { GenreScene sc; std::vector<const char*> expect; const char* what; };
    std::vector<WrongCase> wrong;
    {
        GenreScene s = jazz;
        s.shape = "synthwave";
        wrong.push_back({s, {"balance_sub_high"}, "jazz with a synthwave low end (kick + sub at 40-60 Hz)"});
        s = jazz;
        s.lufs = -9.0;
        s.ceilingDb = -1.5;
        wrong.push_back({s, {"loudness_high", "squashed"}, "jazz mastered like pop (-9 LUFS, limited)"});
        s = jazz;
        s.hallLu = -99.0;
        s.widthPct = 3.0;
        wrong.push_back({s, {"dry_mix", "narrow_mix"}, "jazz dry and mono"});
        s = classical;
        s.sectionDb = {0.0, 0.0, 0.0, 0.0, 0.0};
        s.lufs = -11.0;
        s.ceilingDb = -1.5;
        wrong.push_back({s, {"loudness_high", "squashed", "lra_low"}, "classical flattened and limited to -11 LUFS"});
        s = classical;
        s.tweakDb = {0, 0, 0, 0, 6.0, 0, 0};
        wrong.push_back({s, {"balance_presence_high"}, "classical with steely strings (+6 dB at 2.5-6 kHz)"});
        s = classical;
        s.hallLu = -24.0;
        wrong.push_back({s, {"dry_mix"}, "classical without a hall (reverb 24 LU under the mix)"});
        s = piano;
        s.tweakDb = {0, 11.0, 0, 0, 0, 0, 0};
        wrong.push_back({s, {"balance_bass_high"}, "solo piano with a boomy bottom (+11 dB at 60-250 Hz)"});
        s = piano;
        s.tweakDb = {0, 0, 0, 0, 8.0, 0, 0};
        wrong.push_back({s, {"balance_presence_high"}, "solo piano with a glassy, hard attack (+8 dB at 2.5-6 kHz)"});
        s = pop;
        s.tweakDb = {-14.0, 0, 0, 0, 0, -6.0, -6.0};  // reads ~-7 dB: the analyser's band split leaks some 60-80 Hz into the sub
        wrong.push_back({s, {"balance_sub_low", "dull"}, "pop without low end and top"});
        s = pop;
        s.lufs = -14.0;
        s.ceilingDb = 0.0;
        wrong.push_back({s, {"loudness_low"}, "pop at -14 LUFS"});
        s = pop;
        s.widthPct = 10.0;
        wrong.push_back({s, {"narrow_mix"}, "pop 10 % wide"});
        s = rock;
        s.shape = "synthwave";
        wrong.push_back({s, {"balance_sub_high"}, "rock with a synthwave sub"});
        s = rock;
        s.tweakDb = {0, 0, 0, -7.0, 0, 0, 0};
        wrong.push_back({s, {"balance_mid_low"}, "rock with scooped mids (-7 dB at 0.8-2.5 kHz)"});
        s = rock;
        s.sectionDb = {-22.0, -12.0, 0.0, -2.0};
        s.lufs = -9.0;
        wrong.push_back({s, {"lra_high"}, "rock with a 15+ LU loudness range"});
        s = film;
        s.tweakDb = {-14.0, 0, 0, 0, 0, 0, 0};
        wrong.push_back({s, {"balance_sub_low"}, "film score without low end"});
        s = film;
        s.hallLu = 5.0;
        wrong.push_back({s, {"washy"}, "film score drowned in the hall (reverb 5 dB over the direct sound)"});
        s = film;
        s.lufs = -8.0;
        s.ceilingDb = -1.5;
        wrong.push_back({s, {"loudness_high", "squashed"}, "film score limited to -8 LUFS"});
    }
    for (auto& wc : wrong) {
        bool lra = false;  // the loudness range is judged on songs over 30 s only; the rest runs on short mixes
        for (const char* code : wc.expect) lra = lra || std::string(code).rfind("lra_", 0) == 0;
        if (!lra) wc.sc.sectionSec = 4.5;
        const json r = genreReport(wc.sc);
        bool all = true;
        for (const char* code : wc.expect) all = all && hasWarning(r, code);
        check(all, std::string("'") + wc.sc.profile + "': " + wc.what + " -> flagged (" + profileWarnings(r) + "); " + digest(r));
    }
    std::printf("  genre profiles: %d test mixes, %.0f ms\n", static_cast<int>(std::size(refs) + 4 + wrong.size()),
                std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count());
}

void testSongAndPngs(const std::string& outDir) {
    const double sr = 48000.0;
    const Song song = makeSong(sr);
    as::MixAnalyzer an;
    const auto t0 = std::chrono::steady_clock::now();
    const json r = analyse(an, sr, song.mix, song.nodes, song.ids, song.sections, song.bpm, song.buses);
    const auto t1 = std::chrono::steady_clock::now();
    an.writeImages(outDir);
    const auto t2 = std::chrono::steady_clock::now();
    std::ofstream(outDir + "/report.json") << as::formatReport(r);
    std::printf("  synthetic song: %.1f s audio, analysis %.0f ms, %d PNGs %.0f ms\n", static_cast<double>(song.mix.size()) / sr,
                std::chrono::duration<double, std::milli>(t1 - t0).count(), static_cast<int>(r["images"].size()),
                std::chrono::duration<double, std::milli>(t2 - t1).count());
    // Every image of the set: listed with a description, written, CRCs + Adler-32 valid, 1600 px wide.
    check(r["images"].size() == 6 + 5, "report.images: 6 song-wide images + one zoom per section (5)");
    for (const auto& im : r["images"]) {
        const std::string path = outDir + "/" + im["file"].get<std::string>();
        bool ok = false;
        std::string info;
        try {
            const auto img = as::analysis::decodePng(as::analysis::readFileBytes(path));
            ok = img.width == 1600 && img.height >= 300 && img.height <= 1200 && im["shows"].get<std::string>().size() > 30;
            info = std::to_string(img.width) + "x" + std::to_string(img.height);
        } catch (const std::exception& e) {
            info = e.what();
        }
        check(ok, "PNG written and decodes (CRCs + Adler-32 verified): " + path + " " + info);
    }
    check(r["images"][6]["file"] == "spectrogram_01_intro.png" && r["images"][10]["file"] == "spectrogram_05_chorus2.png",
          "section zooms are numbered in song order and named after the sections");
    check(r["clicks"].empty(), "synthetic song (drums, bass, pad, hats, lead, reverb bus): no clicks" +
                                   (r["clicks"].empty() ? std::string() : " " + r["clicks"].dump()));
    // The legacy single-image entry points still work.
    an.writeSpectrogramPng(outDir + "/legacy_spectrogram.png");
    an.writeOverviewPng(outDir + "/legacy_overview.png");
    check(fs::exists(outDir + "/legacy_spectrogram.png") && fs::exists(outDir + "/legacy_overview.png"),
          "writeSpectrogramPng / writeOverviewPng still write single images");
    check(r["sections"].size() == 5 && r["nodes"].size() == 7, "synthetic song: 5 sections, 7 nodes in the report");
    check(r["timeline"]["rows"].size() == 32, "synthetic song: 32 timeline rows");
    const double chorus = r["sections"][2]["lufs"], brk = r["sections"][3]["lufs"];
    check(chorus > brk + 3.0, fmt("chorus (%.1f LUFS) is louder than the breakdown (%.1f LUFS)", chorus, brk));
    bool kickBass = false;
    for (const auto& s : r["suggestions"]) kickBass = kickBass || s.get<std::string>().find("sidechain") != std::string::npos;
    std::printf("  summary: %s\n", r["summary"].get<std::string>().c_str());
    check(kickBass, "synthetic song: a sidechain suggestion addresses kick vs bass");

    // Determinism: a second run gives the identical report.
    as::MixAnalyzer an2;
    const json r2 = analyse(an2, sr, song.mix, song.nodes, song.ids, song.sections, song.bpm, song.buses);
    check(r2 == r, "analysis is deterministic (identical report on a second run)");
}

}  // namespace

int main(int argc, char** argv) {
    namespace fs = std::filesystem;
    const std::string outDir = argc > 1 ? argv[1] : (fs::temp_directory_path() / "agentsound_test_analysis").string();
    fs::create_directories(outDir);
    try {
        testFft();
        testChecksumsAndZlib();
        testPngRoundTrip(outDir);
        testKWeighting();
        testLoudness();
        testTruePeak();
        testBandsAndStereo();
        testMaskingAndWarnings();
        testExactBoundaries();
        testEdgeCases(outDir);
        testReviewFixes();
        testProfiles();
        testSpace(outDir);
        testSpaceNamesAndSongRouting();
        testGenreProfiles();
        testSongAndPngs(outDir);
    } catch (const std::exception& e) {
        std::printf("[FAIL] exception: %s\n", e.what());
        ++failures;
    }
    std::printf("%s: %d failure(s); sample images in %s\n", failures ? "FAILED" : "PASSED", failures, outDir.c_str());
    return failures ? 1 : 0;
}
