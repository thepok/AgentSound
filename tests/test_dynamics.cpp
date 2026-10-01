// Tests for the note-level dynamics ear (engine/analysis/NoteDynamics): a lead played at one velocity is
// 'flat_dynamics' (warn), a lead with velocity arcs is not, drums / arps / 16th pulses are never flagged, a
// flat counter-line is info, onsets are found in the audio when no notes are known, and the profile sets
// the threshold (jazz stricter than default). Usage: test_dynamics [outDir] (report + tracks.png written there;
// default: <temp>/agentsound_test_dynamics).

#include "analysis/MixAnalyzer.h"
#include "analysis/NoteDynamics.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <functional>
#include <string>
#include <vector>

namespace {

using as::json;
constexpr double kPi = 3.14159265358979323846;
constexpr double kSr = 48000.0, kBpm = 120.0, kBeatSec = 60.0 / kBpm;
constexpr int kBars = 16;
constexpr double kSongSec = kBars * 4 * kBeatSec;  // 32 s
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

struct Note {
    double beat, dur;
    int pitch, vel;
};

struct Part {
    std::string id;
    std::string instrument{"va"};
    std::vector<Note> notes;
    bool routed{true};                                    // give the analyser the notes (else: audio onsets only)
    std::vector<std::string> automated;                   // NodeRouting::automated
    as::json instrumentParams = as::json::object();       // NodeRouting::instrumentParams
    std::function<double(int k, const Note&)> levelDb;   // level of note k (dB re full scale); default: from velocity
    std::vector<Note> triggers;                           // the routing's notes instead of `notes` (a singer's phrase triggers)
    bool audioOnsets{false};                              // NodeRouting::audioOnsets (render JSON analysis.audioOnsets)
    std::vector<float> L, R;
};

// Velocity to amplitude like a fully velocity-sensitive synth: (vel/127)^2.
double velDb(int vel) { return 40.0 * std::log10(vel / 127.0); }

// Renders a part: a sine per note (3 ms attack, gentle decay, 15 ms release at 90 % of the length).
void render(Part& p) {
    const auto n = static_cast<std::size_t>(kSongSec * kSr);
    p.L.assign(n, 0.0f);
    p.R.assign(n, 0.0f);
    for (std::size_t k = 0; k < p.notes.size(); ++k) {
        const Note& nt = p.notes[k];
        const double db = p.levelDb ? p.levelDb(static_cast<int>(k), nt) : velDb(nt.vel);
        const double amp = 0.25 * std::pow(10.0, db / 20.0);
        const double hz = 440.0 * std::pow(2.0, (nt.pitch - 69) / 12.0);
        const double t0 = nt.beat * kBeatSec, len = std::max(0.03, 0.9 * nt.dur * kBeatSec);
        const auto s0 = static_cast<std::size_t>(t0 * kSr), s1 = std::min(n, static_cast<std::size_t>((t0 + len + 0.015) * kSr));
        for (std::size_t s = s0; s < s1; ++s) {
            const double t = static_cast<double>(s - s0) / kSr;
            double env = std::min(1.0, t / 0.003) * std::exp(-t * 1.2);
            if (t > len) env *= std::max(0.0, 1.0 - (t - len) / 0.015);
            const auto v = static_cast<float>(amp * env * std::sin(2.0 * kPi * hz * t));
            p.L[s] += v;
            p.R[s] += v;
        }
    }
}

// A melody with rests and mixed lengths (not a pulse): 5 notes per bar, 1 + .5 + .5 + 1.5 + .5 beats.
std::vector<Note> melody(int basePitch, std::function<int(int)> vel) {
    static const double kDur[] = {1.0, 0.5, 0.5, 1.5, 0.5};
    static const int kStep[] = {0, 2, 4, 7, 5, 9, 7, 4, 2, 0, 12, 11};
    std::vector<Note> out;
    int k = 0;
    for (int bar = 0; bar < kBars; ++bar) {
        double b = bar * 4.0;
        for (double d : kDur) {
            out.push_back({b, d * 0.95, basePitch + kStep[k % 12], vel(k)});
            b += d;
            ++k;
        }
    }
    return out;
}

std::vector<Note> grid(double step, double len, int pitch, int vel) {
    std::vector<Note> out;
    for (double b = 0.0; b < kBars * 4.0 - 1e-9; b += step) out.push_back({b, len, pitch, vel});
    return out;
}

json analyse(std::vector<Part>& parts, const std::string& profile, const std::string& outDir = "") {
    as::MixAnalyzer a;
    a.prepare(kSr, kBpm, {{"verse", 0.0, kSongSec / 2}, {"chorus", kSongSec / 2, kSongSec}}, kSongSec);
    if (!profile.empty()) a.setProfile(profile);
    std::vector<int> idx;
    for (Part& p : parts) {
        render(p);
        idx.push_back(a.addNode(p.id, false));
    }
    for (std::size_t i = 0; i < parts.size(); ++i) {
        if (!parts[i].routed) continue;
        as::NodeRouting r;
        r.instrument = parts[i].instrument;
        r.automated = parts[i].automated;
        r.instrumentParams = parts[i].instrumentParams;
        r.audioOnsets = parts[i].audioOnsets;
        for (const Note& n : parts[i].triggers.empty() ? parts[i].notes : parts[i].triggers) {
            r.notes.emplace_back(n.beat, n.dur);
            r.tones.push_back({n.pitch, n.vel});
        }
        a.setNodeRouting(idx[i], r);
    }
    const std::size_t n = parts.front().L.size();
    std::vector<float> mL(n, 0.0f), mR(n, 0.0f);
    for (const Part& p : parts)
        for (std::size_t s = 0; s < n; ++s) {
            mL[s] += p.L[s];
            mR[s] += p.R[s];
        }
    constexpr int kBlock = 512;
    for (std::size_t s = 0; s < n; s += kBlock) {
        const int f = static_cast<int>(std::min<std::size_t>(kBlock, n - s));
        for (std::size_t i = 0; i < parts.size(); ++i) a.feedNode(idx[i], parts[i].L.data() + s, parts[i].R.data() + s, f);
        a.feedMix(mL.data() + s, mR.data() + s, f);
    }
    json r = a.finish();
    if (!outDir.empty()) {
        std::ofstream(outDir + "/report.json") << as::formatReport(r);
        a.writeImages(outDir);
    }
    return r;
}

const json* node(const json& r, const std::string& id) {
    for (const auto& n : r["nodes"])
        if (n["id"] == id) return &n;
    return nullptr;
}

// The flat_dynamics finding about `id`: its severity ("warn" / "info"), or "" when there is none.
std::string finding(const json& r, const std::string& id) {
    for (const auto& w : r["warnings"]) {
        if (w["code"] != "flat_dynamics" || !w.contains("nodes")) continue;
        for (const auto& n : w["nodes"])
            if (n == id) return w["severity"].get<std::string>();
    }
    return "";
}

void testHelpers() {
    double p10 = 0, p90 = 0;
    std::vector<double> v;
    for (int i = 0; i <= 100; ++i) v.push_back(i * 0.1);
    const double s = as::analysis::percentileSpread(v, &p10, &p90);
    check(std::fabs(p10 - 1.0) < 1e-9 && std::fabs(p90 - 9.0) < 1e-9 && std::fabs(s - 8.0) < 1e-9, "percentileSpread: 10-90 % of 0..10 = 8");
    check(as::analysis::percentileSpread({}) == 0.0 && as::analysis::percentileSpread({3.0}) == 0.0, "percentileSpread of < 2 values = 0");

    // Audio onsets: 40 equal notes of a melody with rests are found (within one), each level within 0.3 dB.
    Part p{"x"};
    p.notes = melody(69, [](int) { return 100; });
    p.notes.resize(40);
    render(p);
    as::analysis::OnsetEnvelope env(kSr);
    env.feed(p.L.data(), p.R.data(), static_cast<int>(p.L.size()));
    env.finalize();
    const auto on = as::analysis::detectOnsets(env);
    std::size_t matched = 0;
    for (const Note& n : p.notes)
        for (double t : on)
            if (std::fabs(t - n.beat * kBeatSec) < 0.02) { ++matched; break; }
    check(on.size() >= 39 && on.size() <= 41 && matched >= 39, fmt("audio onsets: %.0f found, %.0f of 40 notes matched", on.size(), matched));
    std::vector<double> lv;
    for (std::size_t k = 0; k < p.notes.size(); ++k)
        lv.push_back(as::analysis::onsetLevelDb(env, p.notes[k].beat * kBeatSec, k + 1 < p.notes.size() ? p.notes[k + 1].beat * kBeatSec : -1.0));
    const double sp = as::analysis::percentileSpread(lv);
    const double expect = 20.0 * std::log10(0.25) + velDb(100) - 3.0;  // sine RMS = peak - 3 dB
    check(sp < 0.3 && std::fabs(lv[0] - expect) < 1.0,  // (the mean over the first 100 ms: the decay costs ~0.5 dB)
          fmt("onset levels of equal notes: spread %.2f dB, level %.1f (peak sine RMS %.1f)", sp, lv[0], expect));
}

void testFlatAndDynamic(const std::string& outDir) {
    // Flat: the lead at velocities 81-103 through a barely velocity-sensitive patch (~0.5 dB), a flat counter-line,
    // a kick, a 16th arp and an unnamed 16th pulse, all at one velocity.
    auto flatParts = [] {
        std::vector<Part> parts;
        Part lead{"lead"};
        lead.notes = melody(72, [](int k) { return 81 + (k * 7) % 23; });
        lead.levelDb = [](int, const Note& n) { return 0.3 * velDb(n.vel); };  // velocity sensitivity 0.3
        parts.push_back(lead);
        Part counter{"counter"};
        counter.notes = melody(60, [](int) { return 90; });
        for (auto& n : counter.notes) n.beat += 0.25;
        parts.push_back(counter);
        Part kick{"kick", "drums"};
        kick.notes = grid(1.0, 0.25, 36, 110);
        parts.push_back(kick);
        Part arp{"arp"};
        arp.notes = grid(0.25, 0.2, 84, 100);
        parts.push_back(arp);
        Part pulse{"synth"};
        pulse.notes = grid(0.25, 0.2, 79, 100);
        parts.push_back(pulse);
        Part figure{"glass"};  // an arpeggio figure with rests: 16ths and 8ths, short notes
        for (const Note& n : grid(1.0, 0.15, 88, 70))
            for (double off : {0.0, 0.25, 0.5}) figure.notes.push_back({n.beat + off, 0.15, 88 + static_cast<int>(off * 16), 70});
        parts.push_back(figure);
        return parts;
    };
    std::vector<Part> flat = flatParts();
    const json r1 = analyse(flat, "", outDir);
    const json* lead = node(r1, "lead");
    check(lead && lead->contains("dynamics"), "the lead has a dynamics measure");
    if (lead && lead->contains("dynamics")) {
        const json& d = (*lead)["dynamics"];
        check(d["kind"] == "lead" && d["onsets"] == "notes" && d["notes"] == 80, "lead: kind lead, 80 note onsets from the notes");
        check(d["phraseSpreadDb"].get<double>() < 1.5 && d["dynamicsDb"].get<double>() < 1.5 && d["flat"] == true && d["phrases"] == 2,
              fmt("lead: phrase spread %.2f dB (dynamics %.2f) < 1.5, flat, 2 phrases", d["phraseSpreadDb"].get<double>(),
                  d["dynamicsDb"].get<double>()));
        // 0.3 x the (v/127)^2 curve: 12/(ln10 * 92) = 0.057 dB per velocity step
        check(std::fabs(d["velocityDbPer10"].get<double>() - 0.57) < 0.15,
              fmt("lead: measured velocity response %.2f dB per 10 steps (expected ~0.57)", d["velocityDbPer10"].get<double>()));
        check(d["velocity"]["min"] == 81 && d["velocity"]["max"] == 103, "lead: velocity range 81-103 reported");
    }
    check(finding(r1, "lead") == "warn", "flat lead -> flat_dynamics warn");
    std::string msg;
    for (const auto& w : r1["warnings"])
        if (w["code"] == "flat_dynamics" && w["nodes"][0] == "lead") msg = w["message"];
    check(msg.find("81-103") != std::string::npos && msg.find("velocity arcs") != std::string::npos,
          "the message names the velocities and the fix: " + msg);
    check(finding(r1, "counter") == "info", "flat counter-line (melodic, not the lead) -> info");

    // A layered lead (stack): the advice names the first layer's velocity param by its stack address.
    std::vector<Part> stacked = flatParts();
    stacked[0].instrument = "stack";
    stacked[0].instrumentParams = json::parse(R"({"layers": [
        {"id": "piano", "instrument": {"type": "sampler", "params": {"velsens": 0.3}}},
        {"id": "pad", "instrument": {"type": "va", "params": {}}, "level": -12}]})");
    const json rs = analyse(stacked, "");
    std::string smsg;
    for (const auto& w : rs["warnings"])
        if (w["code"] == "flat_dynamics" && w["nodes"][0] == "lead") smsg = w["message"];
    check(smsg.find("layers.piano.velsens 0.30") != std::string::npos,
          "stack lead: the fix names the first layer's velocity param (layers.piano.velsens): " + smsg);
    check(finding(r1, "kick").empty() && finding(r1, "arp").empty() && finding(r1, "synth").empty() && finding(r1, "glass").empty(),
          "kick / arp / 16th pulse / arpeggio figure: not flagged");
    const json* kick = node(r1, "kick");
    const json* arp = node(r1, "arp");
    const json* pulse = node(r1, "synth");
    check(kick && !kick->contains("dynamics"), "drums: no note dynamics measured");
    const json* fig = node(r1, "glass");
    check(arp && (*arp)["dynamics"]["kind"] == "even" && pulse && (*pulse)["dynamics"]["kind"] == "even" && fig &&
              (*fig)["dynamics"]["kind"] == "even",
          "arp id, unnamed 16th pulse and a fast figure of short notes: kind even");
    check(r1["reference"]["noteSpreadMinDb"] == 3.0, "reference.noteSpreadMinDb = 3 (default profile)");
    check(std::filesystem::exists(outDir + "/tracks.png"), "tracks.png written with the flat-dynamics marks");

    // Dynamic: velocity arcs 55-118 with accents through a fully velocity-sensitive sound.
    std::vector<Part> dyn = flatParts();
    dyn[0].notes = melody(72, [](int k) { return 55 + static_cast<int>(63.0 * (0.5 + 0.5 * std::sin(2.0 * kPi * k / 9.0))) - (k % 5 == 2 ? 10 : 0); });
    dyn[0].levelDb = nullptr;
    dyn[1].notes = melody(60, [](int k) { return 60 + (k * 37) % 55; });
    for (auto& n : dyn[1].notes) n.beat += 0.25;
    const json r2 = analyse(dyn, "");
    const json* lead2 = node(r2, "lead");
    check(finding(r2, "lead").empty() && finding(r2, "counter").empty(), "lead + counter with velocity arcs: no flat_dynamics");
    if (lead2) check((*lead2)["dynamics"]["dynamicsDb"].get<double>() > 6.0,
                     fmt("dynamic lead: played dynamics %.1f dB per phrase > 6", (*lead2)["dynamics"]["dynamicsDb"].get<double>()));
}

void testAudioOnsetsAndProfiles() {
    // No notes known (audio clip / no routing): onsets from the audio, the 'hook' id makes it a lead.
    std::vector<Part> parts;
    Part hook{"hook"};
    hook.routed = false;
    hook.notes = melody(72, [](int) { return 100; });
    parts.push_back(hook);
    const json r = analyse(parts, "");
    const json* h = node(r, "hook");
    check(h && h->contains("dynamics") && (*h)["dynamics"]["onsets"] == "audio" && std::abs((*h)["dynamics"]["notes"].get<int>() - 80) <= 2,
          "unrouted hook: ~80 onsets found in the audio");
    check(finding(r, "hook") == "warn", "unrouted flat hook -> flat_dynamics warn");

    // A lead that moves only ~3.3 dB: fine under default (3 dB), flat under jazz (4 dB) and classical (4.5 dB).
    auto midParts = [] {
        std::vector<Part> p;
        Part lead{"melody"};
        // velocities that make +-1.75 dB through a fully velocity-sensitive sound (90..111)
        lead.notes = melody(72, [](int k) {
            return static_cast<int>(std::lround(100.0 * std::pow(10.0, 1.75 * std::sin(2.0 * kPi * k / 7.0) / 40.0)));
        });
        p.push_back(lead);
        return p;
    };
    std::vector<Part> a = midParts(), b = midParts(), c = midParts();
    const json rd = analyse(a, "default"), rj = analyse(b, "jazz"), rc = analyse(c, "classical");
    const double sp = (*node(rd, "melody"))["dynamics"]["dynamicsDb"].get<double>();
    check(sp > 3.0 && sp < 4.0, fmt("~3.4 dB lead measured %.2f dB", sp));
    check(finding(rd, "melody").empty(), "~3.3 dB lead: fine under default");
    check(finding(rj, "melody") == "warn" && rj["reference"]["noteSpreadMinDb"] == 4.0, "~3.3 dB lead: flat under jazz (4 dB)");
    check(finding(rc, "melody") == "warn", "~3.3 dB lead: flat under classical (4.5 dB)");

    // A flat bass line (not a pulse): not judged under default (synth bass pulses are even by design), info under jazz
    // (the walking bass is played).
    auto bassParts = [] {
        std::vector<Part> p;
        Part lead{"lead"};
        lead.notes = melody(72, [](int k) { return 55 + (k * 37) % 60; });
        p.push_back(lead);
        Part bass{"bass"};
        bass.notes = melody(36, [](int) { return 100; });
        p.push_back(bass);
        return p;
    };
    std::vector<Part> bd = bassParts(), bj = bassParts();
    const json rbd = analyse(bd, "default"), rbj = analyse(bj, "jazz");
    const json& dbd = (*node(rbd, "bass"))["dynamics"];
    check(dbd["kind"] == "bass" && dbd["judged"] == false && finding(rbd, "bass").empty(), "flat bass line under default: measured, not judged");
    check(finding(rbj, "bass") == "info" && finding(rbj, "lead").empty() && rbj["reference"]["judgeBassDynamics"] == true,
          "flat bass line under jazz: info (dynamic lead fine)");

    // Chorus-like wobble: the note levels scatter +-3 dB for reasons unrelated to the playing, the velocities
    // (86-96 through 0.3 sensitivity) make ~0.3 dB. The audio spread alone would pass; the velocity part is flat.
    auto wobble = [](std::vector<std::string> automated) {
        std::vector<Part> p;
        Part lead{"lead"};
        lead.notes = melody(72, [](int k) { return 86 + (k * 5) % 11; });
        lead.levelDb = [](int k, const Note& n) {
            const double noise = std::sin(k * 12.9898) * 43758.5453;
            return 0.3 * velDb(n.vel) + 6.0 * (noise - std::floor(noise) - 0.5);
        };
        lead.automated = std::move(automated);
        p.push_back(lead);
        return p;
    };
    std::vector<Part> w1 = wobble({}), w2 = wobble({"instrument.expression"});
    const json rw = analyse(w1, ""), ra = analyse(w2, "");
    const json& dw = (*node(rw, "lead"))["dynamics"];
    check(dw["phraseSpreadDb"].get<double>() > 3.5 && dw["velocityPhraseDb"].get<double>() < 1.0 && finding(rw, "lead") == "warn",
          fmt("wobbly lead with flat velocities: audio %.1f dB, velocities %.1f dB -> warn", dw["phraseSpreadDb"].get<double>(),
              dw["velocityPhraseDb"].get<double>()));
    std::string msg;
    for (const auto& w : rw["warnings"])
        if (w["code"] == "flat_dynamics") msg = w["message"];
    check(msg.find("no played dynamics") != std::string::npos && msg.find("from the sound itself") != std::string::npos,
          "the message says the level variation is the sound's, not the playing's");
    const json& da = (*node(ra, "lead"))["dynamics"];
    check(da["automatedDynamics"] == true && finding(ra, "lead").empty(),
          "the same lead with expression automation: judged by the audio (dynamics may come from the automation) -> fine");
    // A wind player's breath written after the compressor (hornist: the eq 'mic' stage's output / a utility gain)
    // counts the same; an eq band gain or a send does not.
    std::vector<Part> wg = wobble({"fx.5.output"}), wu = wobble({"fx.2.gain"}),
                      wn = wobble({"fx.5.high.gain", "send.hall", "fx.x.output"});
    const json rg = analyse(wg, ""), ru = analyse(wu, ""), rn = analyse(wn, "");
    check((*node(rg, "lead"))["dynamics"]["automatedDynamics"] == true && finding(rg, "lead").empty() &&
              (*node(ru, "lead"))["dynamics"]["automatedDynamics"] == true,
          "a lead whose post-compressor gain stage is automated (fx.<i>.output / gain): automated dynamics -> fine");
    check(!(*node(rn, "lead"))["dynamics"].contains("automatedDynamics") && finding(rn, "lead") == "warn",
          "eq band gains, sends and non-index fx paths are not dynamics automation -> still warns");

    // A singer's vocal: the audio is a sung line with real dynamics, the track's notes are one trigger per phrase (2
    // bars, velocity 127). Judged from the triggers it reads flat; with analysis.audioOnsets the ear hears the audio.
    auto vocal = [](bool audio) {
        std::vector<Part> p;
        Part v{"vocal"};
        v.notes = melody(67, [](int k) { return 55 + static_cast<int>(63.0 * (0.5 + 0.5 * std::sin(2.0 * kPi * k / 9.0))); });
        for (int b = 0; b < kBars; b += 2) v.triggers.push_back({b * 4.0, 7.5, 60, 127});
        v.audioOnsets = audio;
        p.push_back(v);
        return p;
    };
    std::vector<Part> vt = vocal(false), va = vocal(true);
    const json rvt = analyse(vt, "jazz"), rva = analyse(va, "jazz");
    check(finding(rvt, "vocal") == "warn", "a vocal judged by its phrase triggers (one velocity): flat_dynamics (the false alarm)");
    const json& dva = (*node(rva, "vocal"))["dynamics"];
    check(dva["onsets"] == "audio" && finding(rva, "vocal").empty(),
          "with audioOnsets: the onsets come from the audio and the sung dynamics pass");
}

}  // namespace

int main(int argc, char** argv) {
    namespace fs = std::filesystem;
    const std::string outDir = argc > 1 ? argv[1] : (fs::temp_directory_path() / "agentsound_test_dynamics").string();
    fs::create_directories(outDir);
    try {
        testHelpers();
        testFlatAndDynamic(outDir);
        testAudioOnsetsAndProfiles();
    } catch (const std::exception& e) {
        std::printf("[FAIL] exception: %s\n", e.what());
        ++failures;
    }
    std::printf("%s: %d failure(s); report + images in %s\n", failures ? "FAILED" : "PASSED", failures, outDir.c_str());
    return failures ? 1 : 0;
}
