import keyboard
import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo, second2tick
import time as time
import os

TEMPO = 120


port = mido.open_output('Microsoft GS Wavetable Synth 0')
keys = {'a': 60, 'w': 61, 's': 62, 'e': 63, 'd': 64, 'f': 65, 't': 66, 'g': 67, 'y': 68, 'h': 69, 'u': 70, 'j': 71}
pressed_keys = {key: False for key in keys.keys()}
 
mid = MidiFile()
track = MidiTrack()
mid.tracks.append(track)
time_old, time_new = time.time(), 0
track.append(MetaMessage('set_tempo', tempo=bpm2tempo(TEMPO)))
 
def play_midi_file(file_path):
    try:
        mid = MidiFile(file_path)
        for message in mid.play():
            port.send(message)
    except FileNotFoundError:
        print("File not found")
        print('Close app...')
        os._exit(0)
        

def hook(key):
    import time
    global time_old, time_new
    if key.event_type == "down":
        print(key)
        
        if key.name == "esc":
            print('song saved')
            mid.save('new_song.mid')
            print('Close app...')
            os._exit(0)
        
        if key.name == "1":
            print('Playing...')
            play_midi_file('new_song.mid')
            print('Close app...')
            os._exit(0)
        if key.name in keys:
            if not pressed_keys[key.name]:
                time_new = time.time()
                port.send(mido.Message('note_on', note=keys[key.name]))
                track.append(Message('note_on', note=keys[key.name], velocity=64, time=second2tick(time_new-time_old, 480, tempo=bpm2tempo(TEMPO))))
                print(time_new-time_old)
                time_old=time_new
                pressed_keys[key.name] = True

        
    if key.event_type == "up":
        if key.name in keys:
            time_new = time.time()
            port.send(mido.Message('note_off', note=keys[key.name]))
            track.append(Message('note_off', note=keys[key.name], velocity=64, time=second2tick(time_new-time_old, 480, tempo=bpm2tempo(TEMPO))))
            time_old=time_new
            pressed_keys[key.name] = False

print('1: run song')
print('esc: save song')
keyboard.hook(hook)
keyboard.wait()
