// End-to-end renderer tests: parsing, routing, sidechain ordering, automation, modulators,
// master latency compensation, determinism and error reporting.

#include "instruments/Dx7Banks.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
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

json baseSong() {
    json song = json::parse(R"({
      "format": "agentsound.render", "version": 1, "title": "render test",
      "tempo": 120, "lengthBeats": 8, "tailSeconds": 2, "seed": 7,
      "sections": [{"name": "a", "startBeat": 0, "endBeat": 4}, {"name": "b", "startBeat": 4, "endBeat": 8}],
      "tracks": [
        {"id": "kick", "instrument": {"type": "drums", "params": {}}, "output": "drumbus",
         "notes": [[0,0.25,36,120],[1,0.25,36,120],[2,0.25,36,120],[3,0.25,36,120],[4,0.25,36,120],[5,0.25,36,120],[6,0.25,36,120],[7,0.25,36,120]]},
        {"id": "pad", "instrument": {"type": "va", "params": {}},
         "fx": [{"type": "ducker", "sidechain": "kick", "params": {}}],
         "sends": {"hall": -10},
         "notes": [[0,4,57,90],[0,4,60,90],[0,4,64,90],[4,4,53,90],[4,4,57,90],[4,4,60,90]],
         "automation": [{"target": "gainDb", "points": [[0,-24],[4,-6,"smooth"]]},
                        {"target": "pan", "points": [[0,-0.5],[8,0.5]]}]},
        {"id": "keys", "instrument": {"type": "dx7", "params": {"voice": "E.PIANO 1"}}, "gainDb": -4,
         "notes": [[0,1,72,100],[2,1,76,100],[4,1,79,100]],
         "modulators": [{"target": "pan", "source": {"type": "lfo", "shape": "sine", "rateBeats": 2}, "mode": "offset", "depth": 0.4, "base": 0},
                        {"target": "gainDb", "source": {"type": "follow", "node": "kick", "releaseMs": 80}, "mode": "offset", "depth": -4, "base": -4}]}
      ],
      "buses": [
        {"id": "drumbus", "fx": [{"type": "compressor", "params": {}}]},
        {"id": "hall", "fx": [{"type": "reverb", "params": {}}]}
      ],
      "master": {"fx": [{"type": "limiter", "params": {}}]}
    })");
    // The DX7 ROM banks are not distributed (assets/dx7/README.md): without them the keys play a va instead.
    if (!as::dx7BanksInstalled("assets")) song["tracks"][2]["instrument"] = {{"type", "va"}, {"params", json::object()}};
    return song;
}

std::vector<char> readFile(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), {}};
}

// Returns the 24-bit PCM samples (interleaved) of a WAV written by WavWriter.
std::vector<float> readWav24(const fs::path& p) {
    const auto bytes = readFile(p);
    std::vector<float> out;
    for (std::size_t i = 44; i + 2 < bytes.size(); i += 3) {
        std::int32_t v = (static_cast<unsigned char>(bytes[i]) | (static_cast<unsigned char>(bytes[i + 1]) << 8) |
                          (static_cast<unsigned char>(bytes[i + 2]) << 16));
        if (v & 0x800000) v -= 0x1000000;
        out.push_back(static_cast<float>(v) / 8388608.0f);
    }
    return out;
}

bool throwsConfig(const json& doc, const std::string& expectInMessage) {
    try {
        const auto song = as::parseSong(doc);
        as::validateSong(song, "assets");
    } catch (const as::ConfigError& e) {
        const bool matched = std::string(e.what()).find(expectInMessage) != std::string::npos;
        if (!matched) std::cout << "       (message was: " << e.what() << ")\n";
        return matched;
    }
    return false;
}

}  // namespace

int main() {
    const fs::path scratch = fs::path(".scratch") / "render";
    fs::create_directories(scratch);
    std::cout << "test_render\n";
    if (!as::dx7BanksInstalled("assets")) std::cout << "SKIP: dx7 keys track replaced by va (" << as::kDx7NoBanksHint << ")\n";

    // Render twice: must be bit-identical, non-silent, finite, below 0 dBFS.
    as::RenderOptions options;
    options.assetDir = "assets";
    options.quiet = true;
    const auto song = as::parseSong(baseSong());
    options.outDir = (scratch / "a").string();
    const auto r1 = as::renderSong(song, options);
    options.outDir = (scratch / "b").string();
    const auto r2 = as::renderSong(song, options);
    const auto a = readFile(scratch / "a" / "mix.wav");
    const auto b = readFile(scratch / "b" / "mix.wav");
    check(!a.empty() && a == b, "deterministic mix (bit-identical renders)");
    const auto samples = readWav24(scratch / "a" / "mix.wav");
    float peak = 0.0f;
    double energy = 0.0;
    for (float s : samples) { peak = std::max(peak, std::fabs(s)); energy += static_cast<double>(s) * s; }
    check(peak > 0.05f && peak <= 1.0f, "mix is non-silent and within full scale (peak " + std::to_string(peak) + ")");
    check(energy > 0.0 && std::isfinite(energy), "mix energy finite");
    check(r1.seconds >= 4.0 && r1.seconds <= 4.0 + 2.0 + 0.1, "length = 8 beats @120 + tail <= 2 s (" + std::to_string(r1.seconds) + " s)");
    check(fs::exists(scratch / "a" / "report.json"), "report.json written");
    check(fs::exists(scratch / "a" / "spectrogram.png") && fs::exists(scratch / "a" / "overview.png"), "PNGs written");
    (void)r2;

    // Section preview renders only the window.
    as::RenderOptions preview = options;
    preview.outDir = (scratch / "preview").string();
    preview.fromBeat = 4.0;
    preview.toBeat = 6.0;
    preview.pngs = false;
    const auto rp = as::renderSong(song, preview);
    check(rp.seconds >= 1.0 && rp.seconds <= 1.0 + 2.0 + 0.1, "preview window length (" + std::to_string(rp.seconds) + " s)");

    // Modulators end to end: a trance gate on a pad's fader ('x.' in 8th notes, closed steps -60 dB)
    // is plainly audible in the mix, and each open/closed window starts on the beat grid.
    {
        json gated = json::parse(R"({
          "format": "agentsound.render", "version": 1, "tempo": 120, "lengthBeats": 4, "tailSeconds": 0,
          "tracks": [{"id": "pad", "instrument": {"type": "va", "params": {"amp.attack": 0.001, "amp.release": 0.01}},
                      "notes": [[0, 4, 57, 100], [0, 4, 64, 100]],
                      "modulators": [{"target": "gainDb", "source": {"type": "steps", "values": [0, -1], "stepBeats": 0.5},
                                      "mode": "offset", "depth": 60, "base": 0}]}]
        })");
        as::RenderOptions g = options;
        g.outDir = (scratch / "gate").string();
        g.analysis = false;
        as::renderSong(as::parseSong(gated), g);
        const auto pcm = readWav24(scratch / "gate" / "mix.wav");
        double open = 0.0, closed = 0.0;
        for (int w = 0; w < 8; ++w) {  // 0.5-beat windows = 12000 frames; skip the first 480 (10 ms): a
            double e = 0.0;              // modulated fader is smoothed with 2 ms, so gate edges stay crisp
            for (std::size_t i = static_cast<std::size_t>(w * 12000 + 480) * 2; i < static_cast<std::size_t>((w + 1) * 12000) * 2 && i < pcm.size(); ++i) {
                e += static_cast<double>(pcm[i]) * pcm[i];
            }
            (w % 2 == 0 ? open : closed) += e;
        }
        const double ratioDb = 10.0 * std::log10(open / std::max(closed, 1e-30));
        check(open > 0.0 && ratioDb > 40.0, "gate modulator: closed steps " + std::to_string(ratioDb) + " dB below open ones");
    }

    // Error handling.
    json bad = baseSong();
    bad["tracks"][1]["output"] = "nowhere";
    check(throwsConfig(bad, "not a bus id"), "dangling output rejected");
    bad = baseSong();
    bad["buses"][0]["sends"] = {{"hall", -6}};
    bad["buses"][1]["sends"] = {{"drumbus", -6}};
    check(throwsConfig(bad, "routing cycle"), "routing cycle rejected");
    bad = baseSong();
    bad["tracks"][1]["automation"][0]["target"] = "instrument.nonexistent";
    check(throwsConfig(bad, "not an automatable"), "unknown automation target rejected");
    bad = baseSong();
    bad["tracks"][0]["instrument"]["params"]["bogus"] = 1;
    check(throwsConfig(bad, "bogus"), "unknown instrument param rejected");
    bad = baseSong();
    bad["tracks"][1]["notes"][0][2] = 128;
    check(throwsConfig(bad, "pitch"), "out-of-range pitch rejected");
    bad = baseSong();
    bad["tracks"][1]["fx"][0]["type"] = "reverb";
    check(throwsConfig(bad, "sidechain"), "sidechain on an effect without key input rejected");
    bad = baseSong();
    bad["tracks"][1]["fx"].push_back({{"type", "limiter"}});
    check(throwsConfig(bad, "latency"), "latency effect off the master chain rejected");
    bad = baseSong();
    bad["tracks"][0]["modulators"] = json::array({{{"target", "pan"}, {"mode", "offset"}, {"depth", 0.2}, {"base", 0},
                                                   {"source", {{"type", "follow"}, {"node", "keys"}}}}});
    check(throwsConfig(bad, "routing cycle"), "follower cycle (kick follows keys, keys follows kick) rejected");
    bad = baseSong();
    bad["tracks"][2]["modulators"][0]["source"]["rate"] = 2;
    check(throwsConfig(bad, "unknown key 'rate'"), "unknown modulator source key rejected");

    // "analysis": profile + loudness override, strict, and stated in the report.
    {
        const auto readJson = [](const fs::path& p) {
            std::ifstream in(p);
            return json::parse(in);
        };
        const json defReport = readJson(scratch / "a" / "report.json");
        check(song.analysis.profile == "default" && !song.analysis.loudness && defReport["reference"]["profile"] == "default" &&
                  defReport["reference"]["lufsTarget"] == json::array({-12.0, -9.0}),
              "no \"analysis\": profile 'default', target -12..-9 LUFS in the report");
        json doc = baseSong();
        doc["analysis"] = {{"profile", "synthwave"}, {"loudness", {-11, -8}}};
        const auto withAnalysis = as::parseSong(doc);
        check(withAnalysis.analysis.profile == "synthwave" && withAnalysis.analysis.loudness &&
                  withAnalysis.analysis.loudness->first == -11.0 && withAnalysis.analysis.loudness->second == -8.0,
              "\"analysis\": {\"profile\": \"synthwave\", \"loudness\": [-11, -8]} parsed");
        as::RenderOptions o = options;
        o.outDir = (scratch / "profile").string();
        o.pngs = false;
        as::renderSong(withAnalysis, o);
        const json rep = readJson(scratch / "profile" / "report.json");
        check(rep["reference"]["profile"] == "synthwave" && rep["reference"]["lufsTarget"] == json::array({-11.0, -8.0}) &&
                  rep["reference"]["lufsTargetFrom"] == "override" &&
                  rep["summary"].get<std::string>().find("profile synthwave") != std::string::npos,
              "the report states the profile and the overridden loudness target");
        const auto wav = [&](const char* dir) { return readFile(scratch / dir / "mix.wav"); };
        check(wav("profile") == wav("a"), "the analysis settings never change the audio");
        doc = baseSong();
        doc["analysis"] = {{"profile", "darksynth"}};
        check(as::parseSong(doc).analysis.profile == "darksynth" && !as::parseSong(doc).analysis.loudness,
              "\"analysis\": {\"profile\": \"darksynth\"} alone is valid");
        doc["analysis"] = json::object();
        check(as::parseSong(doc).analysis.profile == "default", "an empty \"analysis\" object keeps the defaults");

        const auto rejects = [&](const json& analysis, const std::string& expect) {
            json d = baseSong();
            d["analysis"] = analysis;
            return throwsConfig(d, expect);
        };
        check(rejects({{"profile", "outrun"}}, "unknown analysis profile 'outrun' (profiles: default, synthwave, dreamwave, darksynth, jazz, classical, piano, pop, rock, film)"),
              "unknown profile rejected, message lists the profiles");
        check(rejects({{"profil", "synthwave"}}, "unknown key 'profil'"), "unknown analysis key rejected");
        check(rejects("synthwave", "$.analysis: must be an object"), "non-object analysis rejected");
        check(rejects({{"profile", 3}}, "$.analysis.profile: must be a string"), "non-string profile rejected");
        check(rejects({{"loudness", {-12}}}, "must be [minLufs, maxLufs]"), "loudness with one value rejected");
        check(rejects({{"loudness", {-12, "x"}}}, "must be [minLufs, maxLufs]"), "non-numeric loudness rejected");
        check(rejects({{"loudness", {-9, -12}}}, "min must be < max"), "inverted loudness window rejected");
        check(rejects({{"loudness", {-12, -12}}}, "min must be < max"), "empty loudness window rejected");
        check(rejects({{"loudness", {-100, -9}}}, "-60..0"), "loudness below -60 LUFS rejected");
        check(rejects({{"loudness", {-12, 3}}}, "-60..0"), "loudness above 0 LUFS rejected");
    }

    std::cout << (failures ? "FAILED" : "PASSED") << " (" << failures << " failures)\n";
    return failures ? 1 : 0;
}
