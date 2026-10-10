# Folded Letter Bossa - A&R

verdict: ship
summary: A gentle, singable bossa whose leap-and-sigh hook frames the whole piece (intro, A sections, the C's last
bars, the tag); the A2's sliding Gb7#11 and the C's climb to F6 over a diminished chord give it shape, and the solo
rises to one clear peak before settling.

evidence: 3:16, -16.4 LUFS-I, TP -1.20 dBTP, LRA 5.6 LU, clicks 0, silent notes 0 (piano 420 events), flat_dynamics 0
(piano lead 8.0 dB per phrase, vel 30-118). loudness.png: intro -18.9 -> head -16.7 -> solo -15.4 (short-term max
-12.4 at the solo's C = the planned climax, ~2:12) -> out -17.1 -> tag -18.5 -> end -19.7.
tracks.png: the left hand 2.4-8.4 dB under the melody.

issues (most severe first):
1. [minor] the bossa left hand's comp/bass phrases read partly flat (5/11 phrases under 4.5 dB) - the endless
   bossa_left as specified by the genre (parity), not a lead.   owner: (endless genre)   fix: none here.
2. [minor] the only fast figure is the intro's trill; the climax has none - a tender bossa does not need one, but a
   listener may expect a bigger flourish at the top.   owner: arranger   fix: optional `mem.save()` at the solo C.
3. [minor] LRA 5.6 LU is modest - inherent to a soft bossa and the genre's master.

checklist: [x] a song, not a loop  [x] no beepy lead  [x] lead in front  [x] real dynamics  [x] played (rolled comping,
rubato intro, fermata)  [x] piano harmonized / decorated, fast figures budgeted  [x] warm  [x] straight 8ths
[x] clicks 0, TP <= -1  [x] the brief's form (ABAC), length, sound parity.
keep: the hook and the frame figure; A2's Gb7#11; the C climb to Abdim7; the tag's Ab -> G into F69.
