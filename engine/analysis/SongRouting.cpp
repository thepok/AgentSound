// MixAnalyzer::setRouting: the routing / material of every analysed node from the parsed song (the
// renderer's one call); kept apart so the rest of the analyser does not depend on the song format.

#include "analysis/MixAnalyzer.h"
#include "analysis/MixImpl.h"
#include "render/SongSpec.h"

#include <algorithm>
#include <stdexcept>

namespace as {

void MixAnalyzer::setRouting(const SongSpec& song) {
    auto& m = *impl_;
    if (m.finished) throw std::logic_error("MixAnalyzer::setRouting after finish");
    for (std::size_t i = 0; i < m.nodes.size(); ++i) {
        for (const NodeSpec& spec : song.nodes) {
            if (spec.id != m.nodes[i].id || spec.kind == NodeSpec::Kind::Master) continue;
            NodeRouting r;
            r.output = spec.output;
            // An automated send counts with its loudest automated level: a throw-only send (static -120 dB,
            // automated up on the last note of a phrase) still feeds its return.
            for (const SendSpec& send : spec.sends) {
                const std::string& bus = send.bus;
                double level = send.db;
                for (const AutomationLane& lane : spec.automation) {
                    if (lane.target != "send." + bus || lane.points.empty()) continue;
                    level = lane.points.front().value;
                    for (const AutomationPoint& p : lane.points) level = std::max(level, p.value);
                }
                // A pre-fader (or pre-insert) send ignores the fader: as a post-fader send relative to the node's
                // output it is that much hotter (inserts' gain is not known here).
                if (send.tap != kTapPost) level -= spec.gainDb;
                r.sends.emplace_back(bus, level);
            }
            for (const FxSpec& fx : spec.fx) r.fx.push_back({fx.type, fx.params});
            if (spec.kind == NodeSpec::Kind::Track) {
                r.instrument = spec.instrumentType;
                r.instrumentParams = spec.instrumentParams;
            }
            r.gainDb = spec.gainDb;
            r.pan = spec.pan;
            r.notes.reserve(spec.notes.size());
            r.tones.reserve(spec.notes.size());
            for (const NoteSpec& n : spec.notes) {
                r.notes.emplace_back(n.startBeat, n.durationBeats);
                r.tones.push_back({n.pitch, n.velocity});
            }
            for (const AutomationLane& lane : spec.automation) {
                if (lane.points.size() < 2) continue;
                r.automated.push_back(lane.target);
                NodeRouting::Lane l;
                l.target = lane.target;
                for (const AutomationPoint& p : lane.points)
                    l.points.push_back({p.beat, p.value, p.curve == Curve::Exp ? 1 : p.curve == Curve::Smooth ? 2 : p.curve == Curve::Step ? 3 : 0});
                r.lanes.push_back(std::move(l));
            }
            for (const SilentNoteHint& h : song.analysis.silentNotes)
                if (h.track == spec.id) r.knownSilent.push_back({h.kind, h.message, h.pitches, h.count});
            for (const std::string& t : song.analysis.audioOnsets) r.audioOnsets = r.audioOnsets || t == spec.id;
            for (const ModulatorSpec& mod : spec.modulators) r.automated.push_back(mod.target);
            setNodeRouting(static_cast<int>(i), std::move(r));
            break;
        }
    }
}

}  // namespace as
