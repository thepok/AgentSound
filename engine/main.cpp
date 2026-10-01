// agentsound - offline renderer CLI.
//
//   agentsound render <song.render.json> --out <dir> [--from-beat X] [--to-beat Y] [--no-analysis] [--no-png] [--quiet]
//   agentsound validate <song.render.json>
//   agentsound params [--json|--markdown] [type]
//   agentsound dx7 [--json] [search]
//   agentsound sf2 [--json] [--file F.sf2] [--samples] [search]
//   agentsound zoom <wav> (--at m:ss.sss | --sec X | --beat B (--song F | --tempo T) [--start-beat S]) [--ms 40] [--detail-ms D]
//                   [--channel L|R|both] [--out file.png] [--title TEXT]
//   agentsound clicks <wav> [--json] [--min-jump DB] [--min-contrast DB] [--max-spread X] [--onset-hf-rise DB]
//   agentsound analyze <wav> --out DIR [--profile P] [--loudness MIN,MAX] [--tempo BPM] [--start-beat B]
//                      [--section NAME START END]... [--from T] [--to T] [--title TEXT] [--no-png] [--no-measures]
//                      the render analysis (report.json + images) of any WAV, plus report["measures"]
//                      (analysis/Measures.h); without --tempo the bar grid uses the estimated tempo
//   agentsound compare-png <compare.json> --out <png>
//                      the picture of a reference comparison (python -m agentsound compare)
//   agentsound cover --style S --title T [--subtitle S] [--seed N] [--palette P] [--size 1400] --out cover.png
//                    [--spec cover.json] [--list]
//                      album cover art (art/Cover.h); --list prints the styles and their palettes
//
// Exit codes: 0 ok, 2 invalid input, 1 internal error. One JSON result line on stdout (clicks: the list).

#include "analysis/ClickDetector.h"
#include "analysis/ComparePlot.h"
#include "analysis/FileAnalysis.h"
#include "analysis/WaveZoom.h"
#include "art/Cover.h"
#include "instruments/Dx7Banks.h"
#include "instruments/Sf2File.h"
#include "io/WavReader.h"
#include "render/Registry.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <windows.h>
#include <shellapi.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using as::json;

namespace {

fs::path executableDir() {
    wchar_t buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    return fs::path(std::wstring(buffer, length)).parent_path();
}

std::string assetDir(const std::string& override) {
    if (!override.empty()) return fs::absolute(override).string();
    if (const char* env = std::getenv("AGENTSOUND_ASSETS")) return fs::absolute(env).string();
    for (fs::path dir = executableDir(); !dir.empty(); dir = dir.parent_path()) {
        if (fs::exists(dir / "assets" / "soundfonts") || fs::exists(dir / "assets" / "dx7")) return (dir / "assets").string();
        if (dir == dir.parent_path()) break;
    }
    return (fs::current_path() / "assets").string();
}

int usage() {
    std::cerr << "usage:\n"
                 "  agentsound render <song.render.json> --out <dir> [--from-beat X] [--to-beat Y] [--no-analysis] [--no-png] [--quiet] [--assets DIR]\n"
                 "  agentsound validate <song.render.json> [--assets DIR]\n"
                 "  agentsound params [--json|--markdown] [type]\n"
                 "  agentsound dx7 [--json] [search]\n"
                 "  agentsound sf2 [--json] [--file F.sf2] [--samples] [search]\n"
                 "  agentsound zoom <wav> (--at m:ss.sss | --sec X | --beat B (--song F | --tempo T) [--start-beat S]) [--ms 40] [--detail-ms D]\n"
                 "                  [--channel L|R|both] [--out file.png] [--title TEXT]\n"
                 "  agentsound clicks <wav> [--json] [--min-jump DB] [--min-contrast DB] [--max-spread X] [--onset-hf-rise DB]\n"
                 "  agentsound analyze <wav> --out DIR [--profile P] [--loudness MIN,MAX] [--tempo BPM] [--start-beat B]\n"
                 "                  [--section NAME START END]... [--from T] [--to T] [--title TEXT] [--no-png] [--no-measures]\n"
                 "  agentsound compare-png <compare.json> --out <png>\n"
                 "  agentsound cover --style synthwave|outrun|dreamwave|darksynth|jazz|classical|rock|pop --title T [--subtitle S]\n"
                 "                  [--seed N] [--palette NAME|#rrggbb,#rrggbb] [--size 1400] --out cover.png | --spec cover.json | --list\n";
    return 2;
}

json readJson(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw as::ConfigError("cannot open '" + path + "'");
    try {
        return json::parse(in);
    } catch (const json::parse_error& e) {
        throw as::ConfigError(path + ": invalid JSON: " + e.what());
    }
}

json specToJson(const as::ParamSpec& s) {
    json j = {{"name", s.name}, {"min", s.min}, {"max", s.max}, {"default", s.def},
              {"unit", s.unit}, {"help", s.help}, {"automatable", s.automatable}};
    if (!s.choices.empty()) {
        j["choices"] = s.choices;
        j["default"] = s.choices[static_cast<std::size_t>(s.def + 0.5f)];
    }
    return j;
}

int cmdParams(const std::vector<std::string>& args) {
    std::string format = "text", only;
    for (const auto& a : args) {
        if (a == "--json") format = "json";
        else if (a == "--markdown") format = "markdown";
        else only = a;
    }
    json all = json::object();
    auto add = [&](const std::string& kind, const std::string& type, const std::vector<as::ParamSpec>& specs, bool sidechain) {
        if (!only.empty() && only != type) return;
        json entry = {{"kind", kind}, {"params", json::array()}};
        if (kind == "effect") entry["sidechain"] = sidechain;
        if (kind == "effect" && as::effectRequiresSidechain(type)) entry["sidechainRequired"] = true;
        for (const auto& s : specs) entry["params"].push_back(specToJson(s));
        all[type] = entry;
    };
    for (const auto& t : as::instrumentTypes()) add("instrument", t, as::createInstrument(t)->paramSpecs(), false);
    for (const auto& t : as::effectTypes()) add("effect", t, as::createEffect(t)->paramSpecs(), as::effectAcceptsSidechain(t));
    if (all.empty()) { std::cerr << "unknown type '" << only << "'\n"; return 2; }

    if (format == "json") { std::cout << all.dump(1) << "\n"; return 0; }
    std::ostringstream out;
    const bool md = format == "markdown";
    if (md) out << "# AgentSound parameter reference\n\nGenerated by `agentsound params --markdown`. Ranges are inclusive; enum params take the choice name as a string.\n";
    for (auto it = all.begin(); it != all.end(); ++it) {
        const json& e = it.value();
        if (md) {
            out << "\n## " << it.key() << " (" << e["kind"].get<std::string>()
                << (e.value("sidechainRequired", false) ? ", needs a sidechain" : e.value("sidechain", false) ? ", accepts sidechain" : "") << ")\n\n"
                << "| param | range | default | unit | auto | help |\n|---|---|---|---|---|---|\n";
        } else {
            out << "\n[" << it.key() << "] " << e["kind"].get<std::string>()
                << (e.value("sidechainRequired", false) ? " (needs a sidechain)" : e.value("sidechain", false) ? " (sidechain)" : "") << "\n";
        }
        for (const auto& p : e["params"]) {
            std::ostringstream range;
            if (p.contains("choices")) {
                for (std::size_t i = 0; i < p["choices"].size(); ++i) range << (i ? "|" : "") << p["choices"][i].get<std::string>();
            } else {
                range << p["min"].get<double>() << ".." << p["max"].get<double>();
            }
            std::ostringstream def;
            if (p["default"].is_string()) def << p["default"].get<std::string>(); else def << p["default"].get<double>();
            if (md) {
                out << "| `" << p["name"].get<std::string>() << "` | " << range.str() << " | " << def.str() << " | "
                    << p["unit"].get<std::string>() << " | " << (p["automatable"].get<bool>() ? "yes" : "") << " | "
                    << p["help"].get<std::string>() << " |\n";
            } else {
                out << "  " << p["name"].get<std::string>() << "  " << range.str() << "  default " << def.str() << " "
                    << p["unit"].get<std::string>() << (p["automatable"].get<bool>() ? "" : "  [static]") << "  - "
                    << p["help"].get<std::string>() << "\n";
            }
        }
    }
    std::cout << out.str();
    return 0;
}

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

int cmdDx7(const std::vector<std::string>& args, const std::string& assets) {
    bool asJson = false;
    std::string search;
    for (const auto& a : args) {
        if (a == "--json") asJson = true;
        else search = lower(a);
    }
    if (!as::dx7BanksInstalled(assets)) {
        // The Yamaha ROM cartridges are not distributed with the project: an empty list, not an error.
        std::cerr << as::kDx7NoBanksHint << "\n";
        if (asJson) std::cout << "[]\n";
        return 0;
    }
    json list = json::array();
    for (const auto& v : as::listDx7Voices(assets)) {
        if (!search.empty() && lower(v.name).find(search) == std::string::npos && lower(v.bank).find(search) == std::string::npos) continue;
        list.push_back({{"bank", v.bank}, {"index", v.index}, {"name", v.name}, {"id", v.bank + ":" + std::to_string(v.index)}});
    }
    if (asJson) { std::cout << list.dump(1) << "\n"; return 0; }
    for (const auto& v : list) {
        std::printf("%-8s %2d  %s\n", v["bank"].get<std::string>().c_str(), v["index"].get<int>(), v["name"].get<std::string>().c_str());
    }
    return 0;
}

// SoundFont presets (bank, program, name, id = "bank:program", usable as the sf2 'preset' param) or, with
// --samples, the raw samples (for sampler zones {"file": "soundfonts/<file>", "sample": name}).
int cmdSf2(const std::vector<std::string>& args, const std::string& assets) {
    bool asJson = false, samples = false;
    std::string file = "GeneralUser-GS.sf2", search;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        if (a == "--json") asJson = true;
        else if (a == "--samples") samples = true;
        else if (a == "--file") {
            if (i + 1 >= args.size()) throw as::ConfigError("missing value for --file");
            file = args[++i];
        } else if (!a.empty() && a[0] == '-') throw as::ConfigError("unknown option '" + a + "'");
        else search += (search.empty() ? "" : " ") + lower(a);
    }
    const auto sf = as::sf2::load(as::sf2::resolvePath(assets, file));
    json list = json::array();
    if (!samples) {
        for (const as::sf2::Preset* p : sf->sortedPresets()) {
            const std::string id = std::to_string(p->bank) + ":" + std::to_string(p->program);
            if (!search.empty() && lower(p->name).find(search) == std::string::npos && id != search) continue;
            list.push_back({{"bank", p->bank}, {"program", p->program}, {"name", p->name}, {"id", id}});
        }
    } else {
        for (std::size_t i = 0; i < sf->samples.size(); ++i) {
            const as::sf2::Sample& s = sf->samples[i];
            if (!search.empty() && lower(s.name).find(search) == std::string::npos) continue;
            const bool loop = s.loopEnd > s.loopStart && s.loopStart >= s.start && s.loopEnd <= s.end;
            json e = {{"index", i}, {"name", s.name}, {"rate", s.rate}, {"frames", s.frames()},
                      {"seconds", s.rate ? std::round(1000.0 * s.frames() / s.rate) / 1000.0 : 0.0},
                      {"root", s.pitch <= 127 ? static_cast<int>(s.pitch) : 60}, {"correction", s.correction}};
            if (loop) {
                e["loopStart"] = s.loopStart - s.start;
                e["loopEnd"] = s.loopEnd - s.start;
            }
            list.push_back(e);
        }
    }
    if (asJson) { std::cout << list.dump(1) << "\n"; return 0; }
    if (!samples) {
        for (const auto& p : list) {
            std::printf("%3d %3d  %-24s %s\n", p["bank"].get<int>(), p["program"].get<int>(), p["name"].get<std::string>().c_str(),
                        p["id"].get<std::string>().c_str());
        }
    } else {
        for (const auto& s : list) {
            std::printf("%-22s %6d Hz %7.2f s  root %3d %+4d ct%s\n", s["name"].get<std::string>().c_str(), s["rate"].get<int>(),
                        s["seconds"].get<double>(), s["root"].get<int>(), s["correction"].get<int>(),
                        s.contains("loopStart") ? ("  loop " + std::to_string(s["loopStart"].get<long long>()) + ".." +
                                                   std::to_string(s["loopEnd"].get<long long>())).c_str() : "");
        }
    }
    return 0;
}

// "83.25", "1:23.25" or "1:01:23.25" -> seconds.
double parseTime(const std::string& s) {
    double total = 0.0;
    std::size_t start = 0;
    int parts = 0;
    while (true) {
        const std::size_t colon = s.find(':', start);
        const std::string part = s.substr(start, colon == std::string::npos ? std::string::npos : colon - start);
        std::size_t used = 0;
        double v = 0.0;
        try {
            v = std::stod(part, &used);
        } catch (const std::exception&) {
            used = 0;
        }
        if (part.empty() || used != part.size() || !(v >= 0.0) || ++parts > 3) throw as::ConfigError("bad time '" + s + "' (use m:ss.sss or seconds)");
        total = total * 60.0 + v;
        if (colon == std::string::npos) break;
        start = colon + 1;
    }
    return total;
}

double parseNumber(const std::string& flag, const std::string& v) {
    std::size_t used = 0;
    double x = 0.0;
    try {
        x = std::stod(v, &used);
    } catch (const std::exception&) {
        used = 0;
    }
    if (used != v.size() || !std::isfinite(x)) throw as::ConfigError("bad number '" + v + "' for " + flag);
    return x;
}

std::string timeLabel(double sec) {
    const auto ms = static_cast<long long>(std::llround(std::max(0.0, sec) * 1000.0));
    char buf[64];
    std::snprintf(buf, sizeof buf, "%lld:%02lld.%03lld", ms / 60000, (ms / 1000) % 60, ms % 1000);
    return buf;
}

// A missing or unsupported WAV is an input error (exit 2), not an internal one.
as::WavData wavInfo(const std::string& path) {
    try {
        return as::readWavInfo(path);
    } catch (const std::runtime_error& e) {
        throw as::ConfigError(e.what());
    }
}

// Streams a WAV file through the click detector in 1 s chunks.
as::analysis::ClickDetector scanClicks(const std::string& path, const as::analysis::ClickDetector::Settings& settings, as::WavData& info) {
    info = wavInfo(path);
    as::analysis::ClickDetector det(info.sampleRate, settings);
    const std::int64_t chunk = info.sampleRate;
    for (std::int64_t pos = 0; pos < info.totalFrames; pos += chunk) {
        const as::WavData d = as::readWav(path, pos, chunk);
        if (d.left.empty()) break;
        det.feed(d.left.data(), d.right.data(), static_cast<int>(d.left.size()));
    }
    det.finish();
    return det;
}

int cmdClicks(const std::vector<std::string>& args) {
    std::string wav;
    bool asJson = false;
    as::analysis::ClickDetector::Settings settings;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto value = [&]() -> std::string {
            if (i + 1 >= args.size()) throw as::ConfigError("missing value for " + a);
            return args[++i];
        };
        if (a == "--json") asJson = true;
        else if (a == "--min-jump") settings.minJump = std::pow(10.0, parseNumber(a, value()) / 20.0);
        else if (a == "--min-contrast") settings.minContrastDb = parseNumber(a, value());
        else if (a == "--max-spread") settings.maxSpread = parseNumber(a, value());
        else if (a == "--onset-hf-rise") settings.onsetHfRiseDb = parseNumber(a, value());
        else if (!a.empty() && a[0] == '-') throw as::ConfigError("unknown option '" + a + "'");
        else if (wav.empty()) wav = a;
        else throw as::ConfigError("unexpected argument '" + a + "'");
    }
    if (wav.empty()) throw as::ConfigError("clicks needs a WAV file");
    as::WavData info;
    const auto det = scanClicks(wav, settings, info);
    json list = json::array();
    for (const auto& e : det.events()) {
        const double sec = static_cast<double>(e.sample) / info.sampleRate;
        list.push_back({{"time", timeLabel(sec)}, {"sec", std::round(sec * 10000.0) / 10000.0}, {"jumpDb", std::round(e.jumpDb() * 10.0) / 10.0},
                        {"contrastDb", std::round(e.contrastDb() * 10.0) / 10.0}, {"spread", std::round(e.spread * 100.0) / 100.0},
                        {"hfRiseDb", std::round(e.hfRiseDb * 10.0) / 10.0}, {"channel", e.channels == 1 ? "L" : e.channels == 2 ? "R" : "both"}});
    }
    if (asJson) {
        std::cout << json{{"ok", true}, {"file", wav}, {"seconds", info.durationSec()}, {"clicks", list}}.dump() << "\n";
        return 0;
    }
    std::printf("%s: %.2f s, %d Hz, %d click%s%s\n", wav.c_str(), info.durationSec(), info.sampleRate, static_cast<int>(list.size()),
                list.size() == 1 ? "" : "s", det.overflow() ? " (list truncated)" : "");
    for (const auto& c : list)
        std::printf("  %s  (%.4f s)  jump %.1f dBFS  contrast %.1f dB  spread %.2f  hf rise %+.1f dB  %s\n",
                    c["time"].get<std::string>().c_str(), c["sec"].get<double>(), c["jumpDb"].get<double>(), c["contrastDb"].get<double>(),
                    c["spread"].get<double>(), c["hfRiseDb"].get<double>(), c["channel"].get<std::string>().c_str());
    return 0;
}

// The render's analysis (report.json + images) plus report["measures"] for any WAV file.
int cmdAnalyze(const std::vector<std::string>& args, const std::vector<std::string>& utf8) {
    as::FileAnalysisOptions o;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto value = [&]() -> std::string {
            if (i + 1 >= args.size()) throw as::ConfigError("missing value for " + a);
            return args[++i];
        };
        if (a == "--out") o.outDir = value();
        else if (a == "--profile") o.profile = value();
        else if (a == "--loudness") {
            const std::string v = value();
            const std::size_t comma = v.find(',');
            if (comma == std::string::npos) throw as::ConfigError("--loudness needs MIN,MAX in LUFS, e.g. -12,-9");
            o.loudness = std::make_pair(parseNumber(a, v.substr(0, comma)), parseNumber(a, v.substr(comma + 1)));
        } else if (a == "--tempo") o.tempo = parseNumber(a, value());
        else if (a == "--start-beat") o.startBeat = parseNumber(a, value());
        else if (a == "--from") o.fromSec = parseTime(value());
        else if (a == "--to") o.toSec = parseTime(value());
        else if (a == "--title") {
            value();
            o.title = i < utf8.size() ? utf8[i] : args[i];  // the UTF-8 command line (same position)
        }
        else if (a == "--no-png") o.pngs = false;
        else if (a == "--no-measures") o.measures = false;
        else if (a == "--section") {
            if (i + 3 >= args.size()) throw as::ConfigError("--section needs NAME START END (seconds or m:ss.s)");
            as::SectionMarker s;
            s.name = args[++i];
            s.startSec = parseTime(args[++i]);
            s.endSec = parseTime(args[++i]);
            if (s.name.empty() || !(s.endSec > s.startSec)) throw as::ConfigError("--section " + s.name + ": needs a name and END > START");
            o.sections.push_back(s);
        } else if (!a.empty() && a[0] == '-') throw as::ConfigError("unknown option '" + a + "'");
        else if (o.wavPath.empty()) o.wavPath = a;
        else throw as::ConfigError("unexpected argument '" + a + "'");
    }
    if (o.wavPath.empty()) throw as::ConfigError("analyze needs a WAV file");
    const auto r = as::analyzeWavFile(o);
    json line = {{"ok", true}, {"report", fs::absolute(r.reportPath).string()}, {"out", fs::absolute(o.outDir).string()},
                 {"seconds", std::round(r.seconds * 1000.0) / 1000.0}, {"tempo", r.tempo}, {"tempoFrom", r.tempoFrom}};
    if (r.report.contains("summary")) line["summary"] = r.report["summary"];
    std::cout << line.dump() << "\n";
    return 0;
}

// The command line as UTF-8 (Windows hands main() the ANSI code page, which loses characters of
// cover titles such as umlauts outside it); elsewhere argv is used as is.
std::vector<std::string> utf8Args(int argc, char** argv) {
    std::vector<std::string> out;
    int n = 0;
    LPWSTR* w = CommandLineToArgvW(GetCommandLineW(), &n);
    if (w && n == argc) {
        for (int i = 1; i < n; ++i) {
            const int len = WideCharToMultiByte(CP_UTF8, 0, w[i], -1, nullptr, 0, nullptr, nullptr);
            std::string s(static_cast<std::size_t>(std::max(0, len - 1)), '\0');
            if (len > 1) WideCharToMultiByte(CP_UTF8, 0, w[i], -1, s.data(), len, nullptr, nullptr);
            out.push_back(s);
        }
    } else {
        out.assign(argv + 1, argv + argc);
    }
    if (w) LocalFree(w);
    return out;
}

// Album cover PNG (art/Cover.h). Text options are read from the UTF-8 command line; --spec reads
// {style, title, subtitle, palette, seed, size} from a UTF-8 JSON file instead (what the Python
// build uses).
int cmdCover(const std::vector<std::string>& args, const std::vector<std::string>& utf8) {
    as::art::CoverSpec spec;
    std::string out;
    bool list = false;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto value = [&]() -> std::string {
            if (i + 1 >= args.size()) throw as::ConfigError("missing value for " + a);
            return args[++i];
        };
        // Text values come from the UTF-8 command line (same position).
        auto text = [&]() -> std::string {
            const std::string v = value();
            return i < utf8.size() ? utf8[i] : v;
        };
        if (a == "--style") spec.style = value();
        else if (a == "--title") spec.title = text();
        else if (a == "--subtitle") spec.subtitle = text();
        else if (a == "--palette") spec.palette = value();
        else if (a == "--seed") {
            const double s = parseNumber(a, value());
            if (!(s >= 0.0 && s <= 4294967295.0) || s != std::floor(s)) throw as::ConfigError("--seed must be an integer 0..4294967295");
            spec.seed = static_cast<std::uint64_t>(s);
        } else if (a == "--size") {
            const double s = parseNumber(a, value());
            if (s != std::floor(s) || s < 256.0 || s > 4000.0) throw as::ConfigError("--size must be an integer 256..4000 (px)");
            spec.size = static_cast<int>(s);
        } else if (a == "--out") out = value();
        else if (a == "--list") list = true;
        else if (a == "--spec") {
            const json j = readJson(value());
            if (!j.is_object()) throw as::ConfigError("--spec: expected a JSON object");
            for (auto it = j.begin(); it != j.end(); ++it) {
                const std::string& k = it.key();
                const json& v = it.value();
                auto str = [&]() {
                    if (!v.is_string()) throw as::ConfigError("--spec: '" + k + "' must be a string");
                    return v.get<std::string>();
                };
                auto integer = [&](double lo, double hi) {
                    if (!v.is_number() || v.get<double>() != std::floor(v.get<double>()) || v.get<double>() < lo || v.get<double>() > hi)
                        throw as::ConfigError("--spec: '" + k + "' must be an integer " + std::to_string(static_cast<long long>(lo)) +
                                              ".." + std::to_string(static_cast<long long>(hi)));
                    return v.get<double>();
                };
                if (k == "style") spec.style = str();
                else if (k == "title") spec.title = str();
                else if (k == "subtitle") spec.subtitle = str();
                else if (k == "palette") spec.palette = str();
                else if (k == "seed") spec.seed = static_cast<std::uint64_t>(integer(0.0, 4294967295.0));
                else if (k == "size") spec.size = static_cast<int>(integer(256.0, 4000.0));
                else throw as::ConfigError("--spec: unknown key '" + k + "' (style, title, subtitle, palette, seed, size)");
            }
        } else throw as::ConfigError("unknown option '" + a + "'");
    }
    if (list) {
        json styles = json::object();
        for (const auto& s : as::art::coverStyles()) styles[s] = as::art::coverPalettes(s);
        std::cout << json{{"ok", true}, {"styles", styles}}.dump() << "\n";
        return 0;
    }
    if (out.empty()) throw as::ConfigError("cover needs --out <png>");
    const as::analysis::Image img = as::art::renderCover(spec);
    if (!fs::path(out).parent_path().empty()) fs::create_directories(fs::path(out).parent_path());
    as::analysis::writePng(out, img);
    std::cout << json{{"ok", true}, {"png", fs::absolute(out).string()}, {"style", spec.style}, {"size", spec.size}}.dump() << "\n";
    return 0;
}

// compare.png from the compare.json of `python -m agentsound compare`.
int cmdComparePng(const std::vector<std::string>& args) {
    std::string input, out;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        if (a == "--out") {
            if (i + 1 >= args.size()) throw as::ConfigError("missing value for --out");
            out = args[++i];
        } else if (!a.empty() && a[0] == '-') throw as::ConfigError("unknown option '" + a + "'");
        else if (input.empty()) input = a;
        else throw as::ConfigError("unexpected argument '" + a + "'");
    }
    if (input.empty() || out.empty()) throw as::ConfigError("compare-png needs <compare.json> --out <png>");
    const json cmp = readJson(input);
    if (!fs::path(out).parent_path().empty()) fs::create_directories(fs::path(out).parent_path());
    as::analysis::renderComparePng(cmp, out);
    std::cout << json{{"ok", true}, {"png", fs::absolute(out).string()}}.dump() << "\n";
    return 0;
}

int cmdZoom(const std::vector<std::string>& args) {
    std::string wav, out, channel = "both", title, songFile;
    const double nan = std::numeric_limits<double>::quiet_NaN();
    double sec = nan, beat = nan, tempo = nan, startBeat = 0.0, ms = 40.0, detailMs = nan;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto value = [&]() -> std::string {
            if (i + 1 >= args.size()) throw as::ConfigError("missing value for " + a);
            return args[++i];
        };
        if (a == "--at") sec = parseTime(value());
        else if (a == "--sec") sec = parseNumber(a, value());
        else if (a == "--beat") beat = parseNumber(a, value());
        else if (a == "--tempo") tempo = parseNumber(a, value());
        else if (a == "--song") songFile = value();
        else if (a == "--start-beat") startBeat = parseNumber(a, value());
        else if (a == "--ms") ms = parseNumber(a, value());
        else if (a == "--detail-ms") detailMs = parseNumber(a, value());
        else if (a == "--out") out = value();
        else if (a == "--title") title = value();
        else if (a == "--channel") {
            channel = lower(value());
            if (channel != "l" && channel != "r" && channel != "both") throw as::ConfigError("--channel must be L, R or both");
        } else if (!a.empty() && a[0] == '-') throw as::ConfigError("unknown option '" + a + "'");
        else if (wav.empty()) wav = a;
        else throw as::ConfigError("unexpected argument '" + a + "'");
    }
    if (wav.empty()) throw as::ConfigError("zoom needs a WAV file");
    // Song time: --song (a render JSON or report.json: tempo map + meter) or a constant --tempo (4/4).
    std::optional<as::TempoMap> tempoMap;
    as::MeterMap meter;
    if (!songFile.empty()) {
        const json doc = readJson(songFile);
        const json& timing = doc.contains("render") && doc.at("render").is_object() ? doc.at("render") : doc;
        as::SongTiming t;
        try {
            t = as::parseTiming(timing);
        } catch (const as::ConfigError& e) {
            throw as::ConfigError(songFile + ": " + e.what());
        }
        try {
            tempoMap = t.tempoMap.empty() ? as::TempoMap(t.tempo, t.sampleRate) : as::TempoMap(t.tempoMap, t.sampleRate);
            if (!t.meter.empty()) meter = as::MeterMap(t.meter);
        } catch (const std::invalid_argument& e) {
            throw as::ConfigError(songFile + ": " + e.what());
        }
    } else if (tempo > 0.0) {
        tempoMap = as::TempoMap(tempo, 48000.0);
    }
    auto songSeconds = [&](double b) { return tempoMap->sampleAt(b) / tempoMap->sampleRate(); };
    if (std::isnan(sec)) {
        if (std::isnan(beat)) throw as::ConfigError("zoom needs --at m:ss.sss, --sec X or --beat B (with --song FILE or --tempo T)");
        if (!tempoMap) throw as::ConfigError("--beat needs the song time: --song song.render.json (or report.json) or --tempo BPM");
        sec = songFile.empty() ? (beat - startBeat) * 60.0 / tempo : songSeconds(beat) - songSeconds(startBeat);
    }
    if (!(ms >= 0.2 && ms <= 10000.0)) throw as::ConfigError("--ms must be 0.2..10000 (width of the view in ms)");
    const as::WavData info = wavInfo(wav);
    const double sr = info.sampleRate;
    if (!(sec >= 0.0 && sec <= info.durationSec())) {
        char buf[160];
        std::snprintf(buf, sizeof buf, "time %.4f s is outside the file (0..%.3f s)", sec, info.durationSec());
        throw as::ConfigError(buf);
    }
    const double halfMs = ms / 2.0;
    if (std::isnan(detailMs)) detailMs = std::clamp(ms / 12.0, 0.4, 10.0);
    const auto centre = static_cast<std::int64_t>(std::llround(sec * sr));
    const auto margin = static_cast<std::int64_t>(std::llround((halfMs + 60.0) * 0.001 * sr));  // context for the click detector
    const std::int64_t first = std::max<std::int64_t>(0, centre - margin);
    as::WavData d = as::readWav(wav, first, centre + margin + 1 - first);

    as::analysis::ClickDetector det(sr);
    det.feed(d.left.data(), d.right.data(), static_cast<int>(d.left.size()));
    det.finish();
    as::analysis::WaveZoomSpec spec;
    spec.sampleRate = sr;
    spec.halfMs = halfMs;
    spec.detailHalfMs = detailMs / 2.0;
    spec.showL = channel != "r";
    spec.showR = channel != "l";
    json clicks = json::array();
    std::string clickText;
    for (const auto& e : det.events()) {
        const std::int64_t s = first + e.sample;
        const double rel = static_cast<double>(s - centre) / sr * 1000.0;
        if (std::fabs(rel) > halfMs) continue;
        spec.markers.push_back({rel, "click"});
        clicks.push_back({{"sec", std::round(static_cast<double>(s) / sr * 10000.0) / 10000.0}, {"offsetMs", std::round(rel * 100.0) / 100.0},
                          {"jumpDb", std::round(e.jumpDb() * 10.0) / 10.0}, {"contrastDb", std::round(e.contrastDb() * 10.0) / 10.0}});
        char buf[96];
        std::snprintf(buf, sizeof buf, "%s%+.2f ms (jump %.0f dBFS)", clickText.empty() ? "" : ", ", rel, e.jumpDb());
        clickText += buf;
    }
    const std::string name = fs::path(wav).filename().string();
    as::analysis::WaveSource src;
    src.name = fs::path(wav).stem().string();
    src.centre = centre - first;
    src.L = std::move(d.left);
    src.R = std::move(d.right);
    spec.sources.push_back(std::move(src));
    char head[512];
    std::string pos;
    double songBeat = nan;
    if (!songFile.empty()) {
        songBeat = tempoMap->beatAtSample(tempoMap->sampleAt(startBeat) + sec * tempoMap->sampleRate());
        pos = " | " + meter.label(songBeat);
        if (!tempoMap->constant()) {
            char pb[48];
            std::snprintf(pb, sizeof pb, " | %.1f BPM", tempoMap->bpmAt(songBeat));
            pos += pb;
        }
    } else if (tempo > 0.0) {
        const double b = std::round((startBeat + sec * tempo / 60.0) * 100.0) / 100.0;
        const double bar = std::floor(b / 4.0 + 1e-9);
        char pb[64];
        std::snprintf(pb, sizeof pb, " | bar %d beat %.2f", static_cast<int>(bar) + 1, b - 4.0 * bar + 1.0);
        pos = pb;
        songBeat = startBeat + sec * tempo / 60.0;
    }
    std::snprintf(head, sizeof head, "ZOOM  %s  at %s (%.4f s)%s | %d Hz, %d-bit%s, %d ch", name.c_str(), timeLabel(sec).c_str(), sec,
                  pos.c_str(), info.sampleRate, info.bitsPerSample, info.isFloat ? " float" : "", info.channels);
    spec.title = title.empty() ? head : title;
    spec.subtitle = clicks.empty() ? "no clicks detected in view" : "clicks detected in view (red lines): " + clickText;
    if (out.empty()) {
        char file[128];
        const int m = static_cast<int>(sec / 60.0);
        std::snprintf(file, sizeof file, "zoom_%dm%06.3fs_%s.png", m, sec - 60.0 * m, fs::path(wav).stem().string().c_str());
        out = (fs::path(wav).parent_path() / file).string();
    }
    if (!fs::path(out).parent_path().empty()) fs::create_directories(fs::path(out).parent_path());
    as::analysis::renderWaveZoom(spec, out);
    json result = {{"ok", true}, {"png", fs::absolute(out).string()}, {"sec", sec}, {"sampleRate", info.sampleRate},
                   {"windowMs", ms}, {"clicks", clicks}};
    if (!std::isnan(songBeat)) result["beat"] = std::round(songBeat * 1000.0) / 1000.0;
    std::cout << result.dump() << "\n";
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    std::vector<std::string> args(argv + 1, argv + argc);
    if (args.empty()) return usage();
    const std::string command = args[0];
    args.erase(args.begin());

    std::string assetsOverride;
    for (std::size_t i = 0; i + 1 < args.size(); ++i) {
        if (args[i] == "--assets") { assetsOverride = args[i + 1]; args.erase(args.begin() + static_cast<long>(i), args.begin() + static_cast<long>(i) + 2); break; }
    }
    const std::string assets = assetDir(assetsOverride);

    try {
        if (command == "params") return cmdParams(args);
        if (command == "dx7") return cmdDx7(args, assets);
        if (command == "sf2") return cmdSf2(args, assets);
        if (command == "zoom") return cmdZoom(args);
        if (command == "clicks") return cmdClicks(args);
        if (command == "analyze" || command == "cover") {
            // Titles are UTF-8 text (umlauts, dashes, any script): read them from the wide command line.
            std::vector<std::string> u = utf8Args(argc, argv);
            if (!u.empty()) u.erase(u.begin());  // the command
            // --assets was removed from args above; keep the lists aligned.
            for (std::size_t i = 0; i + 1 < u.size(); ++i)
                if (u[i] == "--assets") { u.erase(u.begin() + static_cast<long>(i), u.begin() + static_cast<long>(i) + 2); break; }
            const std::vector<std::string>& utf8 = u.size() == args.size() ? u : args;
            return command == "analyze" ? cmdAnalyze(args, utf8) : cmdCover(args, utf8);
        }
        if (command == "compare-png") return cmdComparePng(args);

        if (command == "validate" || command == "render") {
            if (args.empty()) return usage();
            const std::string input = args[0];
            as::RenderOptions options;
            options.assetDir = assets;
            for (std::size_t i = 1; i < args.size(); ++i) {
                const std::string& a = args[i];
                auto value = [&]() -> std::string {
                    if (i + 1 >= args.size()) throw as::ConfigError("missing value for " + a);
                    return args[++i];
                };
                if (a == "--out") options.outDir = value();
                else if (a == "--from-beat") options.fromBeat = std::stod(value());
                else if (a == "--to-beat") options.toBeat = std::stod(value());
                else if (a == "--no-analysis") options.analysis = false;
                else if (a == "--no-png") options.pngs = false;
                else if (a == "--quiet") options.quiet = true;
                else throw as::ConfigError("unknown option '" + a + "'");
            }
            const as::SongSpec song = as::parseSong(readJson(input));
            if (command == "validate") {
                as::validateSong(song, assets);
                std::cout << json{{"ok", true}, {"tracks", song.nodes.size() - 1}}.dump() << "\n";
                return 0;
            }
            if (options.outDir.empty()) throw as::ConfigError("render needs --out <dir>");
            const auto result = as::renderSong(song, options);
            json line = {{"ok", true}, {"seconds", result.seconds}, {"renderSeconds", result.renderSeconds},
                         {"mix", result.mixPath}, {"out", fs::absolute(options.outDir).string()}};
            if (!result.reportPath.empty()) line["report"] = result.reportPath;
            std::cout << line.dump() << "\n";
            return 0;
        }
        return usage();
    } catch (const as::ConfigError& e) {
        std::cerr << "error: " << e.what() << "\n";
        std::cout << json{{"ok", false}, {"error", e.what()}}.dump() << "\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "internal error: " << e.what() << "\n";
        std::cout << json{{"ok", false}, {"error", std::string("internal: ") + e.what()}}.dump() << "\n";
        return 1;
    }
}
