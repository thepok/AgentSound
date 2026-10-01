// File analysis (agentsound analyze): analysing a render's own mix.wav with the render's tempo and
// sections reproduces the render's mix numbers; report["measures"] is complete, sane and
// deterministic; tempo estimation; strict errors.

#include "analysis/FileAnalysis.h"
#include "analysis/Measures.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using as::json;

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

bool near(const json& a, const json& b, double tol) {
    return a.is_number() && b.is_number() && std::fabs(a.get<double>() - b.get<double>()) <= tol;
}

json song() {
    json notes = json::array(), bass = json::array(), pad = json::array();
    for (int b = 0; b < 32; ++b) notes.push_back({b, 0.25, 36, 120});
    for (int b = 0; b < 32; b += 2) bass.push_back({b, 1.5, b % 8 < 4 ? 33 : 31, 100});
    for (int b = 0; b < 32; b += 4) {
        for (int p : {57, 60, 64}) pad.push_back({b, 4, p + (b % 8 ? -2 : 0), 85});
    }
    json s = json::parse(R"({
      "format": "agentsound.render", "version": 1, "title": "analyze test",
      "tempo": 124, "lengthBeats": 32, "tailSeconds": 2, "seed": 3,
      "sections": [{"name": "verse", "startBeat": 0, "endBeat": 16}, {"name": "chorus", "startBeat": 16, "endBeat": 32}],
      "buses": [{"id": "hall", "fx": [{"type": "reverb", "params": {"mix": 1.0}}]}],
      "master": {"fx": [{"type": "limiter", "params": {"gain": 6}}]}
    })");
    s["tracks"] = json::array({
        {{"id", "kick"}, {"instrument", {{"type", "drums"}, {"params", json::object()}}}, {"notes", notes}},
        {{"id", "bass"}, {"instrument", {{"type", "va"}, {"params", {{"cutoff", 600}}}}}, {"gainDb", -4}, {"notes", bass}},
        {{"id", "pad"}, {"instrument", {{"type", "va"}, {"params", {{"unison", 5}, {"unison.spread", 0.8}}}}}, {"gainDb", -10},
         {"sends", {{"hall", -8}}}, {"notes", pad}},
    });
    return s;
}

}  // namespace

int main() {
    const fs::path dir = fs::temp_directory_path() / "agentsound_test_analyze_file";
    fs::remove_all(dir);
    as::RenderOptions opt;
    opt.outDir = (dir / "render").string();
    opt.assetDir = "assets";
    opt.pngs = false;
    opt.quiet = true;
    const auto rr = as::renderSong(as::parseSong(song()), opt);
    const json rep = json::parse(std::ifstream(rr.reportPath));

    std::cout << "file analysis reproduces the render's mix numbers\n";
    as::FileAnalysisOptions fo;
    fo.wavPath = rr.mixPath;
    fo.outDir = (dir / "file").string();
    fo.tempo = 124;
    fo.pngs = false;
    for (const auto& s : rep["sections"]) fo.sections.push_back({s["name"].get<std::string>(), s["startSec"].get<double>(), s["endSec"].get<double>()});
    const auto fr = as::analyzeWavFile(fo);
    const json& a = rep["global"];
    const json& b = fr.report["global"];
    check(fs::exists(fr.reportPath), "report.json written");
    check(near(a["durationSec"], b["durationSec"], 0.011), "duration");
    for (const char* k : {"lufsIntegrated", "loudnessRange", "shortTermMax", "momentaryMax", "rmsDb", "crestDb", "samplePeakDb", "widthPct"})
        check(near(a[k], b[k], 0.15), std::string(k) + " " + a[k].dump() + " vs " + b[k].dump());
    check(near(a["truePeakDbtp"], b["truePeakDbtp"], 0.03), "truePeakDbtp");
    for (const char* k : {"stereoCorrelation", "lowEndCorrelation", "spectralTiltDbPerOct"}) check(near(a[k], b[k], 0.02), k);
    for (auto it = a["bandsPct"].begin(); it != a["bandsPct"].end(); ++it) check(near(it.value(), b["bandsPct"][it.key()], 0.15), "band " + it.key());
    bool third = a["thirdOctave"]["vsRefDb"].size() == b["thirdOctave"]["vsRefDb"].size();
    for (std::size_t i = 0; third && i < a["thirdOctave"]["vsRefDb"].size(); ++i)
        third = near(a["thirdOctave"]["vsRefDb"][i], b["thirdOctave"]["vsRefDb"][i], 0.25);
    check(third, "third-octave curve");
    check(rep["sections"].size() == fr.report["sections"].size(), "same sections");
    for (std::size_t i = 0; i < rep["sections"].size() && i < fr.report["sections"].size(); ++i)
        check(near(rep["sections"][i]["lufs"], fr.report["sections"][i]["lufs"], 0.15), "section lufs " + rep["sections"][i]["name"].get<std::string>());
    check(fr.report["render"]["tempoFrom"] == "given" && fr.report["render"]["analyzed"] == "file", "render block says file + given tempo");

    std::cout << "measures\n";
    const json& m = fr.report["measures"];
    check(m.contains("spectrum") && m["spectrum"]["hz"].size() == 30 && m["spectrum"]["db"].size() == 30, "30 third-octave bands");
    check(near(m["loudness"]["integratedLufs"], b["lufsIntegrated"], 0.2), "measures loudness = report loudness");
    check(m["stereo"]["widthPct"].size() == 10 && m["stereo"]["below120Hz"]["correlation"].get<double>() > 0.9, "stereo per octave, mono low end");
    check(m["stereo"]["above150Hz"]["widthPct"].get<double>() > 5.0, "the wide pad is measured above 150 Hz");
    check(m["loudness"]["shortTermLu"].contains("p10") && m["loudness"]["histogram"]["pct"].size() == 40, "loudness distribution");
    check(m["transients"]["low"]["perSec"].get<double>() > 1.0 && m["transients"]["low"]["hitDb"].get<double>() > 3.0, "kick onsets and punch found");
    check(m["decay"].contains("robust") && m["sustain"].contains("robust"), "space estimates say whether they are robust");
    check(std::fabs(m["tempo"]["bpm"].get<double>() - 124.0) < 1.5 || std::fabs(m["tempo"]["bpm"].get<double>() - 62.0) < 1.0,
          "tempo estimate " + m["tempo"].dump());

    std::cout << "estimated grid, excerpt, determinism\n";
    as::FileAnalysisOptions eo;
    eo.wavPath = rr.mixPath;
    eo.outDir = (dir / "excerpt").string();
    eo.pngs = false;
    eo.fromSec = 2.0;
    eo.toSec = 10.0;
    const auto e1 = as::analyzeWavFile(eo);
    check(std::fabs(e1.seconds - 8.0) < 0.01, "excerpt length");
    check(e1.tempoFrom == "estimated" || e1.tempoFrom == "default", "tempo estimated when not given: " + e1.tempoFrom);
    const auto e2 = as::analyzeWavFile(eo);
    check(e1.report == e2.report, "deterministic");

    std::cout << "errors\n";
    auto throwsConfig = [](const as::FileAnalysisOptions& o) {
        try {
            as::analyzeWavFile(o);
        } catch (const as::ConfigError&) {
            return true;
        } catch (...) {
            return false;
        }
        return false;
    };
    as::FileAnalysisOptions bad = eo;
    bad.wavPath = (dir / "missing.wav").string();
    check(throwsConfig(bad), "missing file is a config error");
    bad = eo;
    bad.fromSec = 1000.0;
    bad.toSec = -1.0;
    check(throwsConfig(bad), "empty excerpt is a config error");
    bad = eo;
    bad.profile = "nonsense";
    check(throwsConfig(bad), "unknown profile is a config error");

    std::cout << "tempo estimate of a click track\n";
    {
        const double sr = 48000.0;
        std::vector<float> L(static_cast<std::size_t>(sr * 20), 0.0f);
        for (double t = 0.0; t < 20.0; t += 60.0 / 100.0)
            for (int i = 0; i < 400; ++i) {
                const auto k = static_cast<std::size_t>(t * sr) + static_cast<std::size_t>(i);
                if (k < L.size()) L[k] = static_cast<float>(0.8 * std::exp(-i / 60.0) * std::sin(i * 0.3));
            }
        const auto est = as::analysis::estimateTempo(L.data(), L.data(), L.size(), sr);
        check(std::fabs(est.bpm - 100.0) < 1.0, "100 BPM clicks -> " + std::to_string(est.bpm));
    }
    fs::remove_all(dir);
    std::cout << (failures ? "FAILED: " + std::to_string(failures) : std::string("all passed")) << "\n";
    return failures ? 1 : 0;
}
