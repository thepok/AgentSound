// Silent notes ear (engine/analysis/SilentNotes.h): notes that make no audible sound are flagged in report.json
// ('silent_notes' warnings, nodes[].silentNotes); quiet-but-audible notes, notes under their own sustain, legato
// lines and notes silenced by automation are not; the compiler's analysis.silentNotes are repeated with what the
// render measured.

#include "analysis/SilentNotes.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

namespace fs = std::filesystem;
using as::json;

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

// 120 BPM: a beat is 0.5 s.
json song() {
    return json::parse(R"J({
      "format": "agentsound.render", "version": 1, "title": "silent notes", "tempo": 120, "lengthBeats": 24,
      "tailSeconds": 1, "seed": 3,
      "tracks": [
        {"id": "smp", "instrument": {"type": "sampler", "params": {"samples": [{"file": "*sine", "lo": 60, "hi": 72}]}},
         "notes": [[0,0.5,60,100],[1,0.5,62,100],[2,0.5,64,100],[3,0.5,65,100],[4,0.5,67,100],[5,0.5,69,100],
                   [7,0.5,40,100],
                   [9,0.5,65,30],
                   [11,0.5,40,100],
                   [13,0.5,71,100],[15,4,60,100],[16,0.5,40,100]]},
        {"id": "line", "instrument": {"type": "va", "params": {}}, "gainDb": -6,
         "notes": [[0,1.1,60,90],[1,1.1,62,70],[2,1.1,64,90],[3,1.1,65,60],[4,1.1,67,90],[5,1.1,65,50],[6,1.1,64,90],
                   [7,0.06,66,40],[7.05,1,64,90]]},
        {"id": "faded", "instrument": {"type": "va", "params": {}},
         "notes": [[0,0.5,60,100],[2,0.5,62,100],[4,0.5,64,100],[6,0.5,65,100],[12,0.5,67,100],[14,0.5,65,100],[16,0.5,64,100]],
         "automation": [{"target": "gainDb", "points": [[0,0],[9,0],[10,-120]]}]},
        {"id": "whisper", "instrument": {"type": "sampler", "params": {"samples": [{"file": "*sine"}]}}, "gainDb": -6,
         "notes": [[0,0.5,69,100],[2,0.5,69,100],[4,0.5,69,100],[6,0.5,69,100],[8,0.5,69,4],[12,0.5,69,30]]},
        {"id": "kit", "instrument": {"type": "drums", "params": {}},
         "notes": [[0,0.25,36,110],[1,0.25,38,110],[2,0.25,36,110],[3,0.25,38,110],[4,0.25,36,110],[5,0.25,38,110],
                   [8,0.25,70,110],[10,0.25,36,110],[10,0.25,49,110]]},
        {"id": "stk", "instrument": {"type": "stack", "params": {"layers": [
            {"id": "hi", "instrument": {"type": "va", "params": {}}, "keylo": 48, "keyhi": 84},
            {"id": "lo", "instrument": {"type": "va", "params": {}}, "keylo": 20, "keyhi": 47, "mute": true}]}},
         "notes": [[0,0.5,60,100],[2,0.5,64,100],[4,0.5,67,100],[6,0.5,72,100],[9,0.5,40,100],[12,0.5,60,100]]}
      ],
      "buses": [],
      "master": {"fx": [{"type": "limiter", "params": {}}]},
      "analysis": {"silentNotes": [{"track": "smp", "kind": "no_sound", "pitches": [40], "count": 3, "beats": [7, 11, 16],
                                    "message": "'smp': 3 notes on E2 (40) reach no sample on this instrument (compile time)"}]}
    })J");
}

json readJson(const fs::path& p) {
    std::ifstream in(p);
    return json::parse(in);
}

const json* node(const json& rep, const std::string& id) {
    for (const auto& n : rep["nodes"])
        if (n["id"] == id) return &n;
    return nullptr;
}

std::vector<std::string> silentWarnings(const json& rep, const std::string& id) {
    std::vector<std::string> out;
    for (const auto& w : rep["warnings"])
        if (w["code"] == "silent_notes" && w.contains("nodes") && w["nodes"].size() == 1 && w["nodes"][0] == id)
            out.push_back(w["message"].get<std::string>());
    return out;
}

bool throwsConfig(const json& doc, const std::string& expect) {
    try {
        as::parseSong(doc);
    } catch (const as::ConfigError& e) {
        const bool matched = std::string(e.what()).find(expect) != std::string::npos;
        if (!matched) std::cout << "       (message was: " << e.what() << ")\n";
        return matched;
    }
    return false;
}

}  // namespace

int main() {
    std::cout << "test_silent_notes\n";
    const fs::path scratch = fs::path(".scratch") / "silent_notes";
    fs::create_directories(scratch);

    // thresholds
    check(as::analysis::silentThresholdDb(-20.0) == -60.0, "threshold of an ordinary track (median -20 dBFS): -60 dBFS");
    check(as::analysis::silentThresholdDb(-10.0) == -50.0, "a loud track (median -10): 40 dB under the median");
    check(as::analysis::silentThresholdDb(-50.0) == -80.0, "a quiet track (median -50): 30 dB under the median");
    check(as::analysis::silentThresholdDb(-32.0) == -62.0, "median -32: 30 dB under it (a -60.4 dBFS brush note stays audible)");

    as::RenderOptions o;
    o.assetDir = "assets";
    o.outDir = scratch.string();
    o.quiet = true;
    o.pngs = false;
    as::renderSong(as::parseSong(song()), o);
    const json rep = readJson(scratch / "report.json");

    // the sampler: E2 has no zone
    const json* smp = node(rep, "smp");
    check(smp && smp->contains("silentNotes"), "nodes[].silentNotes on a track with notes");
    if (smp) {
        const json& s = (*smp)["silentNotes"];
        std::cout << "       smp: " << s.dump() << "\n";
        check(s["silent"] == 2, "sampler: the two isolated notes on a key without a zone are silent");
        check(s["pitches"] == json::array({40}), "... and only those (the velocity-30 note, ~25 dB softer, is audible)");
        check(s["compileSilent"] == 3, "the compiler's count is kept");
    }
    const auto smpW = silentWarnings(rep, "smp");
    check(smpW.size() == 1 && smpW[0].find("(compile time)") != std::string::npos &&
              smpW[0].find("the render measured 2 of them silent") != std::string::npos,
          "the compile-time finding is repeated once, with the render's count (the one under a sustained note is masked)");
    if (!smpW.empty()) std::cout << "       " << smpW[0] << "\n";

    // a legato va line with a grace note inside the tail of the note before: nothing silent
    const json* line = node(rep, "line");
    check(line && (*line)["silentNotes"]["silent"] == 0 && silentWarnings(rep, "line").empty(),
          "legato / overlapping line with a grace note: no silent note");

    // notes after a gainDb fade to -120: excused, not warned
    const json* faded = node(rep, "faded");
    if (faded) std::cout << "       faded: " << (*faded)["silentNotes"].dump() << "\n";
    check(faded && (*faded)["silentNotes"]["silent"] == 0 && (*faded)["silentNotes"]["excused"] == 3 &&
              silentWarnings(rep, "faded").empty(),
          "notes under a closed gainDb lane are excused, not warned");

    // a note with an attack of its own, ~84 dB under the others (velocity 4 through velsens 1: ~60 dB): too quiet, info;
    // the velocity-30 one (~25 dB under, under -60 dBFS too) sounds
    const json* wh = node(rep, "whisper");
    if (wh) std::cout << "       whisper: " << (*wh)["silentNotes"].dump() << "\n";
    bool info = false;
    for (const auto& w : rep["warnings"])
        if (w["code"] == "silent_notes" && w["nodes"][0] == "whisper")
            info = w["severity"] == "info" && w["message"].get<std::string>().find("was too quiet to be heard") != std::string::npos;
    check(wh && (*wh)["silentNotes"]["silent"] == 1 && (*wh)["silentNotes"]["at"] == json::array({"3:1"}) && info,
          "a note that sounds but 40+ dB under the track: 'too quiet' (info); a soft one 25 dB under: fine");

    // the drum machine: 70 (maracas) is not one of its pieces; the crash with the kick is masked by the kick
    const json* kit = node(rep, "kit");
    const auto kitW = silentWarnings(rep, "kit");
    check(kit && (*kit)["silentNotes"]["silent"] == 1 && kitW.size() == 1 && kitW[0].find("maracas (70)") != std::string::npos,
          "drum machine: the lone note on an unmapped key is flagged with its GM name");
    if (!kitW.empty()) std::cout << "       " << kitW[0] << "\n";

    // the stack: E2 only reaches the muted layer
    const json* stk = node(rep, "stk");
    const auto stkW = silentWarnings(rep, "stk");
    check(stk && (*stk)["silentNotes"]["silent"] == 1 && stkW.size() == 1 && stkW[0].find("E2 (40)") != std::string::npos,
          "stack: a note that only a muted layer takes is flagged");

    // strict parsing of analysis.silentNotes
    json bad = song();
    bad["analysis"]["silentNotes"][0]["track"] = "nope";
    check(throwsConfig(bad, "'nope' is not a track id"), "analysis.silentNotes: unknown track rejected");
    bad = song();
    bad["analysis"]["silentNotes"][0]["colour"] = 1;
    check(throwsConfig(bad, "unknown key 'colour'"), "analysis.silentNotes: unknown key rejected");
    bad = song();
    bad["analysis"]["silentNotes"][0]["kind"] = "loud";
    check(throwsConfig(bad, "must be 'no_sound' or 'muted_layers'"), "analysis.silentNotes: bad kind rejected");
    bad = song();
    bad["analysis"]["silentNotes"][0]["pitches"] = json::array({200});
    check(throwsConfig(bad, "MIDI notes 0..127"), "analysis.silentNotes: bad pitch rejected");

    // the hint never changes the audio
    json plain = song();
    plain.erase("analysis");
    as::RenderOptions o2 = o;
    o2.outDir = (scratch / "plain").string();
    as::renderSong(as::parseSong(plain), o2);
    const auto bytes = [](const fs::path& p) {
        std::ifstream in(p, std::ios::binary);
        return std::string(std::istreambuf_iterator<char>(in), {});
    };
    check(bytes(scratch / "mix.wav") == bytes(scratch / "plain" / "mix.wav"), "analysis.silentNotes never changes the audio");
    const json rep2 = readJson(scratch / "plain" / "report.json");
    const auto plainW = silentWarnings(rep2, "smp");
    check(plainW.size() == 1 && plainW[0].find("made no sound in the render") != std::string::npos &&
              plainW[0].find("2 notes on E2 (40)") != std::string::npos,
          "without the compiler's hint the render finding stands alone (2 notes on E2)");
    if (!plainW.empty()) std::cout << "       " << plainW[0] << "\n";

    std::cout << (failures ? "FAILED\n" : "all passed\n");
    return failures ? 1 : 0;
}
