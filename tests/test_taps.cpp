// Taps: where a send, a sidechain key and a follow modulator pick up a node's signal ("tap": "post" |
// "prefader" | "prefx" | "pre:<i>", docs/RENDER_FORMAT.md "Taps"). Checked end to end through stems:
//   - "post" written out renders bit-identically to no "tap" at all (the default is unchanged);
//   - "prefader" ignores the fader (gainDb) and the pan, "prefx" the inserts, "pre:<i>" the inserts from i on -
//     each bit-identical to an equivalent post-fader routing;
//   - muted nodes still feed nothing through a pre-fader send; strict parsing of every bad form.

#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <cmath>
#include <cstring>
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

// src (a va line, its own fader / pan / inserts) sends to 'ret' (an empty bus), keys a ducker on 'pad' and is
// followed by a modulator on 'fol''s fader.
json song(float srcGainDb, float srcPan, const json& srcFx, const json& send, const json& duckerExtra,
          const json& followExtra, bool srcMute = false) {
    json s = json::parse(R"({
      "format": "agentsound.render", "version": 1, "title": "taps",
      "tempo": 120, "lengthBeats": 8, "tailSeconds": 0.5, "seed": 3,
      "tracks": [
        {"id": "src", "instrument": {"type": "va", "params": {}},
         "notes": [[0,0.5,60,110],[1,0.5,64,100],[2,1.5,67,120],[4,0.25,72,90],[5,2,55,127]]},
        {"id": "pad", "instrument": {"type": "va", "params": {}}, "gainDb": -6,
         "notes": [[0,8,48,90],[0,8,55,90]]},
        {"id": "fol", "instrument": {"type": "va", "params": {}}, "gainDb": -8,
         "notes": [[0,8,43,90]]}
      ],
      "buses": [{"id": "ret"}],
      "export": {"stems": true, "bitDepth": 32}
    })");
    json& src = s["tracks"][0];
    src["gainDb"] = srcGainDb;
    src["pan"] = srcPan;
    src["fx"] = srcFx;
    src["sends"] = {{"ret", send}};
    if (srcMute) src["mute"] = true;
    json ducker = {{"type", "ducker"}, {"sidechain", "src"}, {"params", {{"depth", 12}}}};
    for (auto it = duckerExtra.begin(); it != duckerExtra.end(); ++it) ducker[it.key()] = it.value();
    s["tracks"][1]["fx"] = json::array({ducker});
    json follow = {{"type", "follow"}, {"node", "src"}, {"releaseMs", 60}};
    for (auto it = followExtra.begin(); it != followExtra.end(); ++it) follow[it.key()] = it.value();
    s["tracks"][2]["modulators"] = json::array({{{"target", "gainDb"}, {"source", follow}, {"mode", "offset"},
                                                 {"depth", -12}, {"base", -8}}});
    return s;
}

std::vector<char> readFile(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), {}};
}

double energy(const fs::path& p) {  // 32-bit float: the samples of the data chunk (no dither)
    const auto b = readFile(p);
    std::size_t start = b.size();
    for (std::size_t i = 12; i + 8 <= b.size();) {
        const std::uint32_t len = static_cast<unsigned char>(b[i + 4]) | (static_cast<unsigned char>(b[i + 5]) << 8) |
                                  (static_cast<unsigned char>(b[i + 6]) << 16) |
                                  (static_cast<std::uint32_t>(static_cast<unsigned char>(b[i + 7])) << 24);
        if (std::string(b.data() + i, 4) == "data") { start = i + 8; break; }
        i += 8 + len + (len & 1);
    }
    double e = 0.0;
    for (std::size_t i = start; i + 3 < b.size(); i += 4) {
        float x;
        std::memcpy(&x, b.data() + i, 4);
        e += static_cast<double>(x) * x;
    }
    return e;
}

fs::path render(const json& doc, const std::string& name) {
    const fs::path dir = fs::path(".scratch") / "taps" / name;
    as::RenderOptions o;
    o.outDir = dir.string();
    o.assetDir = "assets";
    o.quiet = true;
    o.analysis = false;
    o.pngs = false;
    as::renderSong(as::parseSong(doc), o);
    return dir;
}

bool same(const fs::path& a, const fs::path& b, const std::string& stem) {
    const auto x = readFile(a / "stems" / (stem + ".wav")), y = readFile(b / "stems" / (stem + ".wav"));
    return !x.empty() && x == y;
}

bool throwsConfig(const json& doc, const std::string& expect) {
    try {
        as::validateSong(as::parseSong(doc), "assets");
    } catch (const as::ConfigError& e) {
        const bool ok = std::string(e.what()).find(expect) != std::string::npos;
        if (!ok) std::cout << "       (message was: " << e.what() << ")\n";
        return ok;
    }
    return false;
}

json utility(double gainDb) { return {{"type", "utility"}, {"params", {{"gain", gainDb}}}}; }

}  // namespace

int main() {
    std::cout << "test_taps\n";
    const json none = json::array(), noExtra = json::object();
    const json twoUtils = json::array({utility(-9.0), utility(-7.0)});

    // 1. The default is unchanged: "tap": "post" everywhere = no tap keys at all, bit for bit (mix and stems).
    const auto base = render(song(-5, 0.3f, twoUtils, -6, noExtra, noExtra), "base");
    const auto post = render(song(-5, 0.3f, twoUtils, {{"db", -6}, {"tap", "post"}}, {{"tap", "post"}}, {{"tap", "post"}}), "post");
    check(readFile(base / "mix.wav") == readFile(post / "mix.wav"), "\"tap\": \"post\" = default: bit-identical mix");
    for (const char* stem : {"ret", "pad", "fol"})
        check(same(base, post, stem), std::string("\"tap\": \"post\" = default: bit-identical stem '") + stem + "'");

    // 2. prefader: the send / key / follower ignore the source's fader and pan. Source at -30 dB panned hard left with
    //    pre-fader taps == source at 0 dB in the centre with post taps (the fader at unity multiplies by exactly 1).
    const auto pre = render(song(-30, -1.0f, twoUtils, {{"db", -6}, {"tap", "prefader"}}, {{"tap", "prefader"}},
                                 {{"tap", "prefader"}}), "prefader");
    const auto unity = render(song(0, 0.0f, twoUtils, -6, noExtra, noExtra), "unity");
    for (const char* stem : {"ret", "pad", "fol"})
        check(same(pre, unity, stem), std::string("prefader (fader -30 dB, pan -1) = post at unity: stem '") + stem + "'");
    check(!same(pre, base, "ret") && energy(pre / "stems" / "ret.wav") > 2.0 * energy(base / "stems" / "ret.wav"),
          "prefader send is louder than the post send of the -5 dB source");

    // 3. prefx: before every insert. Inserts -16 dB in total with prefx taps == no inserts with post taps.
    const auto prefx = render(song(0, 0.0f, twoUtils, {{"db", -6}, {"tap", "prefx"}}, {{"tap", "prefx"}},
                                   {{"tap", "prefx"}}), "prefx");
    const auto dry = render(song(0, 0.0f, none, -6, noExtra, noExtra), "dry");
    for (const char* stem : {"ret", "pad", "fol"})
        check(same(prefx, dry, stem), std::string("prefx = the dry instrument: stem '") + stem + "'");
    check(same(prefx, render(song(0, 0.0f, twoUtils, {{"db", -6}, {"tap", "pre:0"}}, {{"tap", "pre:0"}},
                                  {{"tap", "pre:0"}}), "pre0"), "ret"), "\"pre:0\" = \"prefx\"");

    // 4. pre:<i>: between the inserts. pre:1 of [u(-9), u(-7)] == prefader of [u(-9)]; pre:2 == prefader.
    const auto pre1 = render(song(-12, 0.0f, twoUtils, {{"db", -6}, {"tap", "pre:1"}}, {{"tap", "pre:1"}},
                                  {{"tap", "pre:1"}}), "pre1");
    const auto one = render(song(-12, 0.0f, json::array({utility(-9.0)}), {{"db", -6}, {"tap", "prefader"}},
                                 {{"tap", "prefader"}}, {{"tap", "prefader"}}), "one");
    for (const char* stem : {"ret", "pad", "fol"})
        check(same(pre1, one, stem), std::string("pre:1 = after the first insert: stem '") + stem + "'");
    check(same(render(song(-12, 0.0f, twoUtils, {{"db", -6}, {"tap", "pre:2"}}, noExtra, noExtra), "pre2"),
               render(song(-12, 0.0f, twoUtils, {{"db", -6}, {"tap", "prefader"}}, noExtra, noExtra), "pf2"), "ret"),
          "pre:<fx count> = prefader");

    // 5. Keys and followers really listen there: a source faded to -60 dB still ducks the pad through a pre-fader
    //    key (post: hardly at all).
    const auto quietPost = render(song(-60, 0.0f, none, -6, noExtra, noExtra), "quietpost");
    const auto quietPre = render(song(-60, 0.0f, none, -6, {{"tap", "prefader"}}, {{"tap", "prefader"}}), "quietpre");
    const double padPre = energy(quietPre / "stems" / "pad.wav"), padPost = energy(quietPost / "stems" / "pad.wav");
    const double folPre = energy(quietPre / "stems" / "fol.wav"), folPost = energy(quietPost / "stems" / "fol.wav");
    check(padPre < 0.9 * padPost, "a pre-fader key ducks the pad although the key's fader is at -60 dB (energy x" +
                                      std::to_string(padPre / padPost) + ")");
    check(folPre < 0.9 * folPost, "a pre-fader follower moves although the followed fader is at -60 dB (energy x" +
                                      std::to_string(folPre / folPost) + ")");

    // 6. A muted node feeds no bus, whatever the tap; it still keys (its taps run).
    const auto muted = render(song(0, 0.0f, twoUtils, {{"db", -6}, {"tap", "prefx"}}, {{"tap", "prefx"}}, noExtra, true),
                              "muted");
    check(energy(muted / "stems" / "ret.wav") == 0.0, "muted source: a prefx send stays silent");
    check(same(muted, prefx, "pad"), "muted source: its prefx key still ducks the pad");

    // 7. Strict.
    check(throwsConfig(song(0, 0, none, {{"db", -6}, {"tap", "pre-fader"}}, noExtra, noExtra), "post|prefader|prefx|pre:"),
          "unknown tap name rejected");
    check(throwsConfig(song(0, 0, none, {{"db", -6}, {"tap", 1}}, noExtra, noExtra), "must be a string"),
          "non-string tap rejected");
    check(throwsConfig(song(0, 0, twoUtils, {{"db", -6}, {"tap", "pre:3"}}, noExtra, noExtra), "has 2 insert(s)"),
          "send pre:<i> beyond the chain rejected");
    check(throwsConfig(song(0, 0, twoUtils, -6, {{"tap", "pre:5"}}, noExtra), "has 2 insert(s)"),
          "sidechain pre:<i> beyond the key's chain rejected");
    check(throwsConfig(song(0, 0, twoUtils, -6, noExtra, {{"tap", "pre:9"}}), "has 2 insert(s)"),
          "follow pre:<i> beyond the followed chain rejected");
    check(throwsConfig(song(0, 0, none, {{"db", -6}, {"level", 1}}, noExtra, noExtra), "unknown key 'level'"),
          "unknown key in a send object rejected");
    check(throwsConfig(song(0, 0, none, {{"tap", "prefader"}}, noExtra, noExtra), "missing required 'db'"),
          "send object without db rejected");
    check(throwsConfig(song(0, 0, none, {{"db", 30}}, noExtra, noExtra), "must be in -120..24"),
          "send object db range checked");
    {
        json d = song(0, 0, none, -6, noExtra, noExtra);
        d["tracks"][1]["fx"] = json::array({{{"type", "eq"}, {"tap", "prefx"}}});
        check(throwsConfig(d, "has no \"sidechain\""), "tap on an effect without a sidechain rejected");
    }

    std::cout << (failures ? "FAILED: " : "all passed") << (failures ? std::to_string(failures) : std::string()) << "\n";
    return failures ? 1 : 0;
}
