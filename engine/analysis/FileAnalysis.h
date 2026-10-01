#pragma once

// Analysis of an audio file: the renderer's analysis (MixAnalyzer: report.json + the images) for any
// WAV - a reference track, a bounce, a render's own mix.wav - plus report["measures"]
// (analysis/Measures.h), the arrangement-independent numbers a reference comparison needs.
// A file has no tracks, buses or routing: the report covers the mix only (no nodes, no 'space' roles).
// `agentsound analyze` is the CLI; analysing a render's mix.wav with the render's tempo and
// sections reproduces the render's own mix numbers (the WAV only adds dither).

#include "analysis/MixAnalyzer.h"

#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace as {

struct FileAnalysisOptions {
    std::string wavPath;
    std::string outDir;                                  // created if missing
    std::string profile;                                 // analysis profile ("" = "default")
    std::optional<std::pair<double, double>> loudness;   // integrated target override [min, max] LUFS
    double tempo{0.0};                                   // BPM of the bar grid; <= 0: estimated from the audio (else 120)
    double startBeat{0.0};                               // song beat of the first analysed sample (bar numbers)
    std::vector<SectionMarker> sections;                 // seconds from the first analysed sample
    double fromSec{0.0};                                 // excerpt [fromSec, toSec) of the file
    double toSec{-1.0};                                  // < 0: to the end
    bool pngs{true};
    bool measures{true};                                 // report["measures"]
    std::string title;                                   // report render.title (default: file name)
};

struct FileAnalysisResult {
    json report;
    std::string reportPath;
    double seconds{0.0};       // analysed length
    double tempo{0.0};         // grid tempo used
    std::string tempoFrom;     // "given" | "estimated" | "default"
};

// Throws ConfigError for a missing/unsupported WAV, an empty excerpt or a bad profile / loudness
// target; std::runtime_error on I/O failure while writing.
FileAnalysisResult analyzeWavFile(const FileAnalysisOptions& options);

}  // namespace as
