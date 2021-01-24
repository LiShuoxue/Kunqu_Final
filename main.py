'''
姓名：李硕学
学号：1800011839
该程序可用来生成昆腔北曲风格吟唱古诗词的工尺谱和midi伴奏

例如：在命令行中输入
python main.py -i test.txt -o test.mid -r 7
即读取歌词文件test.txt，生成行数为7的工尺谱，并输出midi伴奏文件test.mid
'''

from Songwriter import SongWriter
import random
import tkinter as tk
import sys, getopt, re

root = tk.Tk() #图形界面对象的生成

first_order_note = ["G3", "A3", "C4", "D4", "E4", "G4", "A4", "C5"]
notedict = {"C":"1", "D":"2", "E":"3", "G":"5", "A":"6"}
gongchedict = {"G3":"合", "A3":"四", "C4":"上", "D4":"尺", "E4":"工", "G4":"六", "A4":"五", "C5":"仩"}
first_order_prob = [
    [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
]

#导入北昆调式文件
shirabedata = open("TUNECAR", encoding="UTF8").readlines()
shirabelist = []
for lines in shirabedata:
    alist = lines.split()
    if len(alist) == 7:
        shirabelist.append(alist)


def generate_base(nword, start, end):
    """
    输入一句的字数nword，起始音符start和终止音符end，
    生成该句音调的大致走向
    """
    newlist = [0] * nword
    newlist[0], newlist[-1] = start, end
    complete = False
    while not complete:
        for x in range(1, nword - 1):
            newlist[x] = random.choices(range(8), weights=first_order_prob[newlist[x - 1]], k=1)[0]
        if first_order_prob[newlist[-2]][end] == 1.0:
            complete = True
    return newlist

def generate_notes(base, tonelist):
    """
    给定一句的基础音符列表base和该句声调的列表tonelist，
    输出这一句的曲谱列表（工尺谱、音符-时值显式）
    """
    notelist = []
    notepool = [[x[6], x[5]] for x in shirabelist]
    for x in range(len(base) - 1):
        weightlist = [0.0] * len(shirabelist)
        for y in range(len(shirabelist)):
            if shirabelist[y][0] == first_order_note[base[x]]:
                if shirabelist[y][3][base[x + 1]] == '1':
                    if shirabelist[y][4][tonelist[x] - 1] == '1':
                        weightlist[y] = 1.0
        notelist.append(random.choices(notepool, weights=weightlist, k=1)[0])
        
    notelist.append([
        first_order_note[base[-1]].lower() + "12-r04",
        gongchedict[first_order_note[base[-1]]],
    ])

    return(notelist)

def write_gongche(character, note, xc, yc, w, end=False):
    """
    输入字character、工尺谱记号note、字的中心位置(xc, yc)、tkinter画布对象w和是否为尾音的bool值end，
    在画布上显示对应字的工尺谱。
    """
    w.create_text(xc, yc, text=character, font=("宋体", "44"), fill="#800000")
    xnote = xc + 40
    ynote = yc - 20
    for char in note:
        if char != "√":
            w.create_text(xnote, ynote, text=char, font=("隶书", "12"), fill="#800000")
            ynote += 15
        else:
            w.create_text(xnote + 10, ynote - 7.5, text="√", fill="#800000")
    if end:
        w.create_text(xnote+5, ynote - 12.5, text="___", font=("隶书", "12", "bold"), fill="#800000")

def repre_note(notetype):
    """
    输入某个字曲谱的音符-时值显式notetype，
    将其转化为Songwriter兼容的音符列表
    """
    repre_note_list = []
    notetype = notetype.replace("\n", "")
    raw_list = notetype.split("-")
    for notes in raw_list:
        note, time = notes[0:2], eval(notes[2:]) / 8.0
        repre_note_list.append([note, time])
    return(repre_note_list)

def compose(lyric_filename, midi_filename, nrow=9):
    """
    输入歌词文件名lyric_filename、待输出midi文件名midi_filename和工尺谱行数nrow，
    在图形界面上展示工尺谱面，并输出midi文件
    """
    lyric = open(lyric_filename, encoding="UTF8")
    line, notelist, write = "", [], False
    score = {
        "major": "f",
        "tempo": 35,
        "channellist": [0, 1],
        "tonelist": [72, 115],
        "melody": [
            {"notes": [], "options": {}},
            {"notes": [], "options": {}}
        ]
    } #初始化曲谱

    while not re.search("END\sLYRICS", line):
        if re.search("BEGIN\sLYRICS", line):
            write = True
        if write == True and not re.search("BEGIN\sLYRICS", line):
            lyr, tone, startnote, endnote = line.split() #手动输入声调时的情况
            nchar = len(lyr)
            tonelist = [eval(tone[x]) for x in range(nchar)]
            start = first_order_note.index(startnote)
            end = first_order_note.index(endnote)
            notes = generate_notes(generate_base(nchar, start, end), tonelist)
            #print([x[1] for x in notes])
            for x in range(nchar):
                if x != nchar - 1:
                    notelist.append([lyr[x], notes[x][1], False])
                else:
                    notelist.append([lyr[x], notes[x][1], True])
                notes_to_be_written = repre_note(notes[x][0])
                for note_to_be_written in notes_to_be_written:
                    score["melody"][0]["notes"].append(note_to_be_written)
            #加入板
            score["melody"][1]["notes"].append(["r0", nchar])
            score["melody"][1]["notes"].append(["c4", 1])

        line = lyric.readline()
        #读入主调式
        if re.search("MAJOR", line):
            score["major"] = line.split()[2].lower()
        #读入节奏快慢（默认1分钟35拍）
        if re.search("TEMPO", line):
            score["tempo"] = eval(line.split()[2])

    #输出伴奏的midi文件
    sr = SongWriter(2, score, midi_filename)
    sr.makesong()

    #绘制工尺谱
    nnote = len(notelist)
    ncol = nnote // nrow + 1
    myheight = (nrow + 1) * 65 - 10
    mywidth = (ncol + 1) * 100
    canvas = tk.Canvas(root, height=myheight, width=mywidth, background="#EEE8AA")
    canvas.pack()
    for x in range(nnote):
        colindex = x // nrow
        rowindex = x % nrow
        character, note, myend = notelist[x]
        write_gongche(character, note,
        mywidth - 100 * (colindex + 1),
        65 * (rowindex + 1), canvas, end=myend)
    canvas.mainloop()

if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], "i:r:o:")
    lyrics_file, midi_file, nrow = "", "", 0
    for op, value in opts:
        if op == "-i":
            lyrics_file = value
        if op == "-r":
            nrow = eval(value)
        if op == "-o":
            midi_file = value

    compose(lyrics_file, midi_file, nrow)
