#include "analysis/FileAnalysis.h"

#include "analysis/Measures.h"
#include "io/WavReader.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace as {

namespace {

// A missing or unsupported WAV is an input error, not an internal one.
WavData wavInfo(const std::string& path) {
    try {
        return readWavInfo(path);
    } catch (const std::runtime_error& e) {
        throw ConfigError(e.what());
    }
}

}  // namespace

FileAnalysisResult analyzeWavFile(const FileAnalysisOptions& o) {
    namespace fs = std::filesystem;
    if (o.outDir.empty()) throw ConfigError("analyze needs --out <dir>");
    const WavData info = wavInfo(o.wavPath);
    if (info.sampleRate < 8000 || info.sampleRate > 384000)
        throw ConfigError("'" + o.wavPath + "': sample rate " + std::to_string(info.sampleRate) + " Hz is outside 8..384 kHz");
    const double sr = info.sampleRate;
    const double dur = info.durationSec();
    if (!(o.fromSec >= 0.0)) throw ConfigError("--from must be >= 0");
    const double to = o.toSec < 0.0 ? dur : std::min(o.toSec, dur);
    if (!(to - o.fromSec > 0.05)) {
        char buf[200];
        std::snprintf(buf, sizeof buf, "the excerpt %.3f..%.3f s is empty (the file is %.3f s long)", o.fromSec, to, dur);
        throw ConfigError(buf);
    }
    const auto first = static_cast<std::int64_t>(std::llround(o.fromSec * sr));
    const auto last = static_cast<std::int64_t>(std::llround(to * sr));
    std::vector<float> L, R;
    L.reserve(static_cast<std::size_t>(last - first));
    R.reserve(static_cast<std::size_t>(last - first));
    const std::int64_t chunk = static_cast<std::int64_t>(sr) * 10;
    for (std::int64_t pos = first; pos < last; pos += chunk) {
        WavData d;
        try {
            d = readWav(o.wavPath, pos, std::min(chunk, last - pos));
        } catch (const std::runtime_error& e) {
            throw ConfigError(e.what());
        }
        if (d.left.empty()) break;
        L.insert(L.end(), d.left.begin(), d.left.end());
        R.insert(R.end(), d.right.begin(), d.right.end());
    }
    for (std::size_t i = 0; i < L.size(); ++i) {  // non-finite float samples: silence (counted by the analyser anyway)
        if (!std::isfinite(L[i])) L[i] = 0.0f;
        if (!std::isfinite(R[i])) R[i] = 0.0f;
    }

    FileAnalysisResult res;
    res.seconds = static_cast<double>(L.size()) / sr;
    analysis::TempoEstimate est;
    if (o.tempo > 0.0) {
        if (!(o.tempo >= 20.0 && o.tempo <= 400.0)) throw ConfigError("--tempo must be 20..400 BPM");
        res.tempo = o.tempo;
        res.tempoFrom = "given";
    } else {
        est = analysis::estimateTempo(L.data(), R.data(), L.size(), sr);
        const bool ok = est.bpm >= 60.0 && est.bpm <= 200.0 && est.confidence >= 0.1;
        res.tempo = ok ? est.bpm : 120.0;
        res.tempoFrom = ok ? "estimated" : "default";
    }

    MixAnalyzer analyzer;
    std::vector<SectionMarker> sections = o.sections;
    analyzer.prepare(sr, res.tempo, sections, res.seconds);
    analyzer.setStartBeat(o.startBeat);
    try {
        analyzer.setProfile(o.profile.empty() ? std::string("default") : o.profile);
        if (o.loudness) analyzer.setLoudnessTarget(o.loudness->first, o.loudness->second);
    } catch (const std::invalid_argument& e) {
        throw ConfigError(e.what());
    }
    constexpr std::size_t kFeed = 8192;
    for (std::size_t i = 0; i < L.size(); i += kFeed) {
        const int n = static_cast<int>(std::min(kFeed, L.size() - i));
        analyzer.feedMix(L.data() + i, R.data() + i, n);
    }
    json report = analyzer.finish();
    json render = {{"title", o.title.empty() ? fs::path(o.wavPath).filename().string() : o.title},
                   {"source", fs::absolute(o.wavPath).string()},
                   {"analyzed", "file"},
                   {"tempo", res.tempo},
                   {"tempoFrom", res.tempoFrom},
                   {"fromBeat", o.startBeat},
                   {"sampleRate", info.sampleRate},
                   {"channels", info.channels},
                   {"bitsPerSample", info.bitsPerSample},
                   {"fromSec", o.fromSec},
                   {"toSec", to},
                   {"fileSeconds", dur}};
    if (res.tempoFrom != "given") render["tempoEstimate"] = {{"bpm", est.bpm}, {"confidence", std::round(est.confidence * 1000.0) / 1000.0}};
    report["render"] = render;
    if (o.measures) report["measures"] = analysis::measureSignal(L.data(), R.data(), L.size(), sr);

    fs::create_directories(o.outDir);
    res.reportPath = (fs::path(o.outDir) / "report.json").string();
    {
        std::ofstream out(res.reportPath, std::ios::binary);
        if (!out) throw std::runtime_error("cannot write '" + res.reportPath + "'");
        out << formatReport(report);
    }
    if (o.pngs) analyzer.writeImages(o.outDir);
    res.report = std::move(report);
    return res;
}

}  // namespace as
