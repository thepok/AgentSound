"""The making-of of Ghosts of Ocean Drive - a night drive, told as one.

The story in the logs: a one-line wish for a new synth song (BRIEF.md), a hook sound chosen by a measured shoot-out
of four candidates (SOUND.md), a sax solo by the wind player, and an A&R verdict that the energy arc went flat after
the first chorus, the kick was soft and the hook had no top (AR.md) - then the revision that made it climb. The film
rides the synthwave grid for the choruses, a ring for the sax, and plays the A&R's bars before and after.
Every line restates the song's files.
"""

from agentsound.makingof.film import AR, Episode, Film, Item, N

NIGHT = 'Warm and cool at once, a late-night radio host.'
FIX = 'Determined, then quietly relieved.'


def build(facts):
    f = Film(facts)
    f.look(scenes={
        'intro': 'nebula', 'verse1': 'grid', 'pre1': 'nebula+hw', 'chorus1': 'grid+hw', 'interlude': 'ring',
        'verse2': 'grid', 'pre2': 'nebula+hw', 'chorus2': 'grid+hw', 'breakdown': 'scope', 'solo': 'ring',
        'chorus3': 'mandala', 'outro': 'nebula',
    })

    f.cold_open(
        N("It started with one line in a chat: start a new synthy song.", NIGHT),
        N("The brief: an eighties night drive in B minor, a singable hook on a hero sound, and a sax solo.", NIGHT),
        N("This is how Ghosts of Ocean Drive was made.", NIGHT, pause=650),
    )
    f.team(
        N("A producer, an arranger, a sound designer, a mix and a mastering engineer, and the A&R. And four "
          "players: the pianist, the drummer, the bassist and the wind player.", NIGHT, pause=650),
    )
    f.blueprint(
        N("Twelve sections, 124 bars at 104 BPM. The last chorus climbs a whole step, to C-sharp minor.", NIGHT),
        N("The energy climbs from -19.7 LUFS in the intro to -9.6 in the last chorus.", NIGHT, pause=650),
        show=('form', 'energy', 'hook'),
    )

    items = {i['name']: i for i in facts['items']}
    pick = [n for n in ('Drums', 'bass', 'Synths', 'lead', 'sax') if n in items]
    f.tracks(
        N("The hook sound was chosen by measurement: four candidates, the same chorus, loudness-matched.", NIGHT),
        N("The synth piano won: the only one with the bed 3.7 dB under the hook and no balance warning.", NIGHT,
          pause=650),
        items=[Item(n, items[n]['ids'], items[n]['at']) for n in pick],
    )
    f.performance()

    f.crisis(
        AR("Verdict: revise."),
        AR("The energy arc flattens after 1:14, and the climax never arrives."),
        N("Every issue went back to the role that owns its cause.", 'Low and serious.', pause=650),
    )
    f.tried(
        N("The judged build against today, the same bars, loudness-matched.", 'Low and serious.'),
        episodes=[
            Episode(2, before_lines=[AR("The drums don't hit like an 80s record: a soft kick under ticky hats.")],
                    after_lines=[N("A LinnDrum kick layered under the kit: kick punch from 13.6 to 18.7 dB.", FIX)]),
            Episode(3, before_lines=[AR("The hook has no top: the high piano key sounds muffled and boxy.")],
                    after_lines=[N("A glass octave layer and an air shelf: the hook's presence share from 0.9 to "
                                   "2.7 %.", FIX)]),
        ],
    )
    f.song(N("And now, Ghosts of Ocean Drive.", 'Hushed anticipation, uplifting.', pause=900))
    f.credits()
    return f
