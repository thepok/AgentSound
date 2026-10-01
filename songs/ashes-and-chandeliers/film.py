"""The making-of of Ashes and Chandeliers - a film in the song's own shape.

The story in the logs: a wish for a Queen-sized epic (BRIEF.md), a piece in four parts with their own keys, tempi and
meters (ARRANGEMENT.md), a curtain motif that returns in every part, and an A&R verdict that sent it back: the
finale buried its own theme, the band arrived quieter than the opera before it, no wall of guitars (AR.md). So the
film is told like the piece: four acts, each under its own light (a candle for the ballad, a ring of voices for the
opera, the note highway for the stampede, a mandala for the curtain), then the verdict and the fix, bar for bar,
then the whole song. Every line restates the song's files; numbers are the logged ones.
"""

from agentsound.makingof.film import AR, Episode, Excerpt, Film, Item, N

WARM = 'Warm, intimate, unhurried.'
STORY = 'Clear and curious, a storyteller.'
TENSE = 'Low and serious, a little tense.'
FIX = 'Determined, then quietly relieved.'


def build(facts):
    f = Film(facts)
    sec = {s['name']: s for s in facts['sections']}

    # the song's light, part by part: candle and dusk for the ballad, rings of voices for the opera, the note
    # highway and the scope for the rock, the mandala for the finale, the candle again for the coda
    f.look(scenes={
        'intro': 'ink', 'theme': 'ink', 'theme2': 'nebula', 'middle': 'nebula', 'return': 'ink',
        'stab': 'ring', 'calls': 'ring', 'masque': 'scope', 'ascent': 'nebula+hw',
        'riff': 'scope', 'anthem': 'nebula+hw', 'anthem2': 'ring', 'solo': 'nebula+hw', 'riff2': 'scope',
        'break': 'ring', 'finale': 'mandala', 'summit': 'mandala', 'fall': 'ink', 'coda': 'ink',
    })

    f.cold_open(
        N("It started with a wish in a chat, about Queen.", WARM),
        N("The brief: an original, multi-part instrumental in the spirit of Bohemian Rhapsody. "
          "Nothing lifted, only the spirit.", WARM),
        N("This is how Ashes and Chandeliers was made: symphonic rock in four parts, five minutes fifty-two.", WARM,
          pause=650),
    )

    f.team(
        N("The producer wrote the brief. The arranger laid out nineteen sections in 132 bars, with rubato, "
          "three ritardandi, an accelerando and three fermatas.", STORY),
        N("A pianist, a drummer, a bassist and a guitarist played the parts; their logs keep every move.", STORY),
        N("Then sound design, mix and master, and the critic: the A&R.", STORY, pause=650),
    )

    f.blueprint(
        N("Four parts, each with its own key, tempo and meter: C minor at 72, E minor at 112 with a waltz in "
          "three-four, A minor at 138, and C major at 76.", STORY),
        N("The hook is the curtain motif: G, E-flat, D, C. An upbeat, a sixth up, then a sigh down by step.", STORY),
        N("It returns nineteen times, handed from the piano to the choirs, the flutes, the guitars and the "
          "orchestra.", STORY, pause=650),
        show=('form', 'tempo', 'hook'),
    )

    # the four acts, each played under its own scene
    f.act('I Candlelight',
          N("Act one, Candlelight. The hero piano alone: rolled chords in the pedal, the theme, and the strings "
            "entering by degrees.", WARM),
          scene='ink', at='theme', play=11)
    f.act('II The Masquerade',
          N("Act two, the Masquerade. A chromatic shock from A-flat to E minor, then the men's choir calls, and "
            "the women answer.", STORY),
          scene='ring', at='calls', play=10)
    f.act('III The Stampede',
          N("Act three, the Stampede. The band kicks in at 138, and a guitar orchestra plays the theme in thirds.",
            'Energetic, with a grin.'),
          scene='nebula+hw', at='anthem2', play=10)
    f.act('IV Curtain',
          N("Act four, Curtain. The theme in C major, a film tutti, the loudest part of the song.",
            'Broad and moved.'),
          scene='mandala', at='finale', play=11)

    items = {i['name']: i for i in facts['items']}
    pick = [n for n in ('Strings', 'Choirs', 'Brass', 'kit', 'Guitars', 'piano', 'Guitars (3 heroes)') if n in items]
    f.tracks(
        N("Every part got its sound for a reason, and the reason is in SOUND.md. Here they are, one by one, "
          "and then the band comes back in.", 'Close, attentive and precise.'),
        items=[Item(n if n != 'Guitars (3 heroes)' else 'Guitar orchestra', items[n]['ids'], items[n]['at'])
               for n in pick],
    )

    solo = sec['solo']['start'] - 3.0           # into the solo: the drummer's flam fill, then the lead guitar
    f.performance(
        excerpts=[Excerpt(round(solo, 2), round(solo + 11, 2), 'solo', [
            N("Into the solo: the drummer's flam fill and crash, then the guitarist's pull-off, bend and hammer-on. "
              "Every label is a move from the players' logs, on its frame.", 'Lively and observant.')])],
    )

    f.crisis(
        AR("Verdict: revise."),
        AR("One blocker, three majors, three minors. The blocker: the finale's payoff is buried. The theme in "
           "C major does not lead the tutti."),
        N("Every issue went back to the role that owns its cause.", TENSE, pause=650),
    )

    f.tried(
        N("Here is what the A&R heard, and what the revision did: the judged build against today, the same bars, "
          "loudness-matched.", TENSE),
        episodes=[
            Episode(1, before_lines=[AR("The finale buries its own theme: the tune's doublings sit 1.7 dB "
                                        "under the rest.")],
                    after_lines=[N("The fix: a film tutti, the theme in three octaves. Now the doublings sit 5.6 "
                                   "dB over the rest.", FIX)]),
            Episode(2, before_lines=[AR("The band's entry is an anticlimax. Bar 74, the fermata: -10.1 LUFS. "
                                        "Bar 75, the riff: -13.7.")],
                    after_lines=[N("Now the fermata dies away into the drummer's pickup, and the riff arrives at "
                                   "-12.6 LUFS, over the fermata's -12.7.", FIX)]),
            Episode(3, before_lines=[AR("No wall of guitars: the rock sections are narrow, heavy on bass and kit.")],
                    after_lines=[N("The rhythm pair came up and the harmony guitars went wide: width above 150 "
                                   "Hz in the anthem from 23 to 31.7 %.", FIX)]),
        ],
    )

    f.song(
        N("After seven renders of revision, the verdict proposal: ship candidate. And now, Ashes and Chandeliers.",
          'Hushed anticipation, uplifting.', pause=900),
    )
    f.credits()
    return f
