"""
Songwriter包通过字典格式的乐谱来生成midi文件
"""

from mido import MidiTrack, Message, MidiFile
import numpy as np


class TrackWriter:
    """
    输入音乐的调式、速度、乐谱等信息，写入一段音轨
    """
    def __init__(self, track, score, channel, major="c", tempo=80):
        self.track = track
        self.score = score
        self.major = major
        self.tempo = tempo
        self.channel = channel
        self.notes = score["notes"]
        self.durs = np.asarray([x[1] for x in self.notes])
        self.beats = np.cumsum(self.durs)

    def add_note(
        self, note, duration, start=0, volume=75,
        octave=0, tempo=80, chan=0, major="c", change=0,
        start_type="beat", switch="openclose",
        ctrls=[], cvalues=[]
            ):
        if note == "r0": #休止符
            real_vol = 0
            real_note = 60
        else:
            nlp = [
                "c", "c+", "d", "d+", "e", "f",
                "f+", "g", "g+", "a", "a+", "b"
                ]
            nlm = [
                "c", "d-", "d", "e-", "e", "f",
                "g-", "g", "a-", "a", "b-", "b"
                ]

            n = note[0:-1]
            try:
                f1 = nlp.index(n)
            except ValueError:
                f1 = nlm.index(n)
            except ValueError:
                raise ValueError("Please input correct note!")
            try:
                f2 = nlp.index(major)
            except ValueError:
                f2 = nlm.index(major)
            except ValueError:
                raise ValueError("Please input correct note!")

            height = eval(note[-1])
            if f2 > 6:
                f2 -= 12

            real_vol = int(1.27 * volume)
            real_note = f1 + f2 + 12 * (height + 1 + octave) + change

        real_dur = int(28800 / tempo * duration)
        real_st = 0

        if start_type == "beat":
            real_st = int(28800 / tempo * start)
        elif start_type == "time":
            real_st = int(480 * start)
        else:
            raise ValueError("Please input correct start_type:\
                'beat' or 'time'.")

        if ctrls is not []:
            for i in range(len(ctrls)):
                mc = Message("control_change", channel=chan, control=ctrls[i], value=cvalues[i], time=0)
                self.track.append(mc)

        if switch == "openclose":
            mstart = Message(
                "note_on", note=real_note, velocity=real_vol,
                time=real_st, channel=chan
                )
            mend = Message(
                "note_off", note=real_note, velocity=real_vol,
                time=real_dur, channel=chan
                )
            self.track.append(mstart)
            self.track.append(mend)
        elif switch == "open":
            mstart = Message(
                "note_on", note=real_note, velocity=real_vol,
                time=real_st, channel=chan
                )
            self.track.append(mstart)
        elif switch == "close":
            mend = Message(
                "note_off", note=real_note, velocity=real_vol,
                time=real_dur, channel=chan
                )
            self.track.append(mend)
        else:
            raise ValueError("Please input corrrect switch:\
                'open', 'close' or 'openclose'.")

    def get_volumes(self):
        vctrl = self.score["options"]["volume"]
        if len(self.beats) - 1 != vctrl[-1][1]:
            raise ValueError("The number of notes are", len(self.beats), "\n\
                but the last note in volume control is", vctrl[-1][1])
        vlist = [0] * len(self.beats)
        for i in range(len(vctrl)):
            vlist[vctrl[i][1]] = vctrl[i][0]
        for j in range(len(vctrl) - 1):
            for k in range(vctrl[j][1] + 1, vctrl[j + 1][1]):
                vol = vctrl[j][0] + (vctrl[j + 1][0] - vctrl[j][0])\
                    / (self.beats[vctrl[j + 1][1]] - self.beats[vctrl[j][1]])\
                    * (self.beats[k] - self.beats[vctrl[j][1]])
                vlist[k] = vol
        return vlist

    def write_a_track(self):
        try:
            namelist = self.score["options"].keys()
            if namelist == []:
                raise KeyError("no keys in namelist")
        except KeyError:
            for i in range(len(self.notes)):
                self.add_note(
                    self.notes[i][0], self.notes[i][1],
                    tempo=self.tempo, chan=self.channel, major=self.major,
                    )
        else:
            oclist = [0] * len(self.notes)
            cglist = [0] * len(self.notes)
            ctrnamedict = {
                "pedal": 64,
                "tweak": 1
            }
            ctrllist = []
            for i in range(len(self.notes)):
                ctrllist.append([])
            cvaluelist = []
            for i in range(len(self.notes)):
                cvaluelist.append([])
            vlist = [75] * len(self.notes)
            for name in namelist:
                if name == "octave":
                    for se in self.score["options"]["octave"]:
                        oc, start, end = se
                        oclist[start:end + 1] = [oc] * (end + 1 - start)
                elif name == "tonechange":
                    for se in self.score["options"]["tonechange"]:
                        cg, start, end = se
                        cglist[start:end + 1] = [cg] * (end + 1 - start)
                elif name == "volume":
                    vlist = self.get_volumes()
                else:
                    ctrlnum = ctrnamedict[name]
                    for msgs in self.score["options"][name]:
                        ctrllist[msgs[1]].append(ctrlnum)
                        cvaluelist[msgs[1]].append(msgs[0])

            for i in range(len(self.notes)):
                self.add_note(
                    self.notes[i][0], self.notes[i][1],
                    volume=vlist[i], octave=oclist[i], change=cglist[i],
                    chan=self.channel, major=self.major, tempo=self.tempo,
                    ctrls=ctrllist[i], cvalues=cvaluelist[i]
                )


class SongWriter:
    """
    整合乐谱中不同音轨的信息，将音乐写入midi文件
    """
    def __init__(self, numtr, json, out):
        self.file = MidiFile()
        self.tracks = self.file.tracks
        self.numtr = numtr
        for x in range(self.numtr):
            self.tracks.append(MidiTrack())
        self.out = out
        self.json = json
        
    def makesong(self):
        part = self.json
        major = part["major"]
        tempo = part["tempo"]
        channellist = part["channellist"]
        tonelist = part["tonelist"]
        melody = part["melody"]
        for x in range(self.numtr):
            tw = TrackWriter(
                self.tracks[x], melody[x],
                channellist[x], major, tempo
                )
            self.tracks[x].append(Message(
                "program_change", channel=channellist[x],
                program=tonelist[x]
                ))
            tw.write_a_track()

        self.file.save(self.out)