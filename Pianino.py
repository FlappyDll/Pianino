import pygame
import keyboard
import mido
import mido.backends.rtmidi
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo, second2tick
import time as time
import os
import sys
import sqlite3
from pygame import locals as pygame_locals

TEMPO = 120

port = mido.open_output('Microsoft GS Wavetable Synth 0')
keys = {'a': 60, 'w': 61, 's': 62, 'e': 63, 'd': 64, 'f': 65, 't': 66, 'g': 67, 'y': 68, 'h': 69, 'u': 70, 'j': 71}
pressed_keys = {key: False for key in keys.keys()}


mid = MidiFile()
track = MidiTrack()
mid.tracks.append(track)
time_old, time_new = time.time(), 0
track.append(MetaMessage('set_tempo', tempo=bpm2tempo(TEMPO)))

# Подключение к базе данных
conn = sqlite3.connect('piano_tracks.db')
cursor = conn.cursor()

# Создание таблицы, если она не существует
cursor.execute("CREATE TABLE IF NOT EXISTS tracks (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")

def generate_next_filename(db_file='piano_tracks.db'):
    # Установка соединения с базой данных
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Проверка были ли записи в базе данных
    cursor.execute("SELECT EXISTS(SELECT 1 FROM sqlite_sequence LIMIT 1)")
    result = cursor.fetchone()[0]
    if(result):
        cursor.execute("SELECT seq + 1 FROM sqlite_sequence")
        next_id = cursor.fetchone()[0]
    else:
        next_id = 1

    # Формирование имени файла
    filename = f"track_{next_id}.mid"

    return filename

# Получение всех сохраненных файлов из базы данных
def get_saved_tracks():
    cursor.execute("SELECT name FROM tracks")
    return cursor.fetchall()

# Добавление нового трека в базу данных
def add_track_to_database(track_name):
    cursor.execute("INSERT INTO tracks (name) VALUES (?)", (track_name,))
    conn.commit()


# Отображение окна выбора сохраненных файлов
class TrackSelector:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Пианино")

        self.screen_width, self.screen_height = 800, 400
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        self.clock = pygame.time.Clock()

        self.saved_tracks = self.get_saved_tracks()
        if self.saved_tracks:
            self.font = pygame.font.Font(None, 24)

            self.scroll_offset = 0
            self.visible_tracks = min(len(self.saved_tracks), 5)  # Максимум 5 видимых треков

            self.play_button_label = self.font.render("Play", True, pygame.Color("white"))
            self.play_button_rect = self.play_button_label.get_rect(center=(self.screen_width / 2, self.screen_height - 40))

    def get_saved_tracks(self):
        cursor.execute("SELECT name FROM tracks")
        return cursor.fetchall()

    def play_midi_file(self, file_path):
        print(f"Playing track: {file_path}")
        try:
            mid = MidiFile(file_path)
            for message in mid.play():
                port.send(message)
        except FileNotFoundError:
            print("File not found")

    def show_saved_tracks(self):
        if get_saved_tracks():
            pygame.init()
            pygame.display.set_caption("Select a track to play")

            self.screen_width, self.screen_height = 400, 300
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

            self.clock = pygame.time.Clock()
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Левая кнопка мыши
                        mouse_pos = pygame.mouse.get_pos()
                        for index, track_rect in enumerate(self.track_rects):
                            if track_rect.collidepoint(mouse_pos):
                                selected_track = self.saved_tracks[index + self.scroll_offset][0]
                                self.play_midi_file(selected_track)
                                running = False

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:  # Прокрутка колесика мыши вверх
                        self.scroll_offset = max(self.scroll_offset - 1, 0)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:  # Прокрутка колесика мыши вниз
                        self.scroll_offset = min(self.scroll_offset + 1, len(self.saved_tracks) - self.visible_tracks)

                self.screen.fill(pygame.Color("black"))

                self.track_labels = []
                self.track_rects = []

                for index, track in enumerate(self.saved_tracks):
                    if index < self.scroll_offset or index >= self.scroll_offset + self.visible_tracks:
                        continue

                    track_label = self.font.render(track[0], True, pygame.Color("white"))
                    self.track_labels.append(track_label)

                    track_rect = track_label.get_rect(center=(self.screen_width / 2, (index - self.scroll_offset + 1) * 40))
                    self.track_rects.append(track_rect)

                for track_label, track_rect in zip(self.track_labels, self.track_rects):
                    self.screen.blit(track_label, track_rect)

                pygame.draw.rect(self.screen, pygame.Color("gray"), self.play_button_rect)
                self.screen.blit(self.play_button_label, self.play_button_rect)

                pygame.display.flip()
                self.clock.tick(60)
        else:
            print("No saved tracks found.")


def update_database(directory=os.getcwd(), db_file='piano_tracks.db'):
    if get_saved_tracks():

        # Получение текущего списка файлов в базе данных
        cursor.execute("SELECT name FROM tracks")
        db_files = cursor.fetchall()
        db_files = [file[0] for file in db_files]

        # Сканирование директории с MIDI-файлами
        for filename in os.listdir(directory):
            if filename.endswith(".mid"):
                file_path = os.path.join(directory, filename)

                # Если файл уже присутствует в базе данных, пропустить его
                if filename in db_files:
                    continue

                # Вставка нового файла в базу данных
                cursor.execute("INSERT INTO tracks (name) VALUES (?)", (filename,))
                conn.commit()
                print(f"Добавлен новый файл: {filename}")

        # Проверка наличия файлов в базе данных, которых нет в директории
        for db_file in db_files:
            if db_file not in os.listdir(directory):
                # Удаление файла из базы данных
                cursor.execute("DELETE FROM tracks WHERE name=?", (db_file,))
                conn.commit()
                print(f"Файл удален из базы данных: {db_file}")

    else:
        print("No saved tracks found.")




# Инициализация Pygame
pygame.init()

# Определение размеров окна
window_width, window_height = 800, 400

# Определение цветов
white = (255, 255, 255)
black = (0, 0, 0)
gray = (160, 160, 160)

# Определение размеров клавиш
key_width = window_width // 14
key_height = window_height // 2
key_spacing = key_width // 8

# Создание окна
window = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption("Пианино")

def play_midi_file(file_path):
    try:
        mid = MidiFile(file_path)
        for message in mid.play():
            port.send(message)
    except FileNotFoundError:
        print("File not found")

def draw_piano():
    window.fill(white)
    for i, key in enumerate(keys.keys()):
        key_x = i * key_width
        key_rect = pygame.Rect(key_x, 0, key_width, key_height)

        if i % 12 in {1, 3, 6, 8, 10}:
            key_color = gray
        else:
            key_color = white

        if key in pressed_keys and pressed_keys[key]:
            key_color = black

        pygame.draw.rect(window, key_color, key_rect)
        pygame.draw.rect(window, gray, key_rect, 1)
        pygame.display.update(key_rect)

    # Отрисовка клавиш внизу окна
    bottom_rect = pygame.Rect(0, key_height, window_width, window_height - key_height)
    pygame.draw.rect(window, black, bottom_rect)

    # Отрисовка текста на клавишах внизу окна
    font = pygame.font.Font(None, 30)
    text_play = font.render("Play", True, white)
    text_exit = font.render("Exit", True, white)
    text_save = font.render("Save", True, white)
    play_rect = text_play.get_rect(center=(window_width // 4, key_height + (window_height - key_height) // 2))
    exit_rect = text_exit.get_rect(center=(window_width // 2, key_height + (window_height - key_height) // 2))
    save_rect = text_save.get_rect(center=(window_width * 3 // 4, key_height + (window_height - key_height) // 2))
    window.blit(text_play, play_rect)
    window.blit(text_exit, exit_rect)
    window.blit(text_save, save_rect)
    pygame.display.update(bottom_rect)

def hook(key):
    import time
    global time_old, time_new
    if key.event_type == "down":
        print(key)

        if key.name == "esc":
            print('Close app...')
            os._exit(0)

        if key.name in keys:
            if not pressed_keys[key.name]:
                time_new = time.time()
                port.send(mido.Message('note_on', note=keys[key.name]))
                track.append(Message('note_on', note=keys[key.name], velocity=64,
                                     time=second2tick(time_new - time_old, 480, tempo=bpm2tempo(TEMPO))))
                print(time_new - time_old)
                time_old = time_new
                pressed_keys[key.name] = True

    if key.event_type == "up":
        if key.name in keys:
            time_new = time.time()
            port.send(mido.Message('note_off', note=keys[key.name]))
            track.append(Message('note_off', note=keys[key.name], velocity=64,
                                 time=second2tick(time_new - time_old, 480, tempo=bpm2tempo(TEMPO))))
            time_old = time_new
            pressed_keys[key.name] = False


keyboard.hook(hook)

# Определение прямоугольников для клавиш внизу окна
play_rect = pygame.Rect(0, key_height, window_width // 3, window_height - key_height)
exit_rect = pygame.Rect(window_width // 3, key_height, window_width // 3, window_height - key_height)
save_rect = pygame.Rect((window_width // 3) * 2, key_height, window_width // 3, window_height - key_height)


# Главный цикл игры
selector = TrackSelector()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for i, key in enumerate(keys.keys()):
                key_x = i * key_width
                key_rect = pygame.Rect(key_x, 0, key_width, key_height)
                if key_rect.collidepoint(mouse_pos):
                    if not pressed_keys[key]:
                        time_new = time.time()
                        port.send(mido.Message('note_on', note=keys[key]))
                        track.append(Message('note_on', note=keys[key], velocity=64,
                                             time=second2tick(time_new - time_old, 480, tempo=bpm2tempo(TEMPO))))
                        print(time_new - time_old)
                        time_old = time_new
                        pressed_keys[key] = True
        elif event.type == pygame.MOUSEBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            for i, key in enumerate(keys.keys()):
                key_x = i * key_width
                key_rect = pygame.Rect(key_x, 0, key_width, key_height)
                if key_rect.collidepoint(mouse_pos):
                    pressed_keys[key] = False  
            # Обработка события нажатия на кнопку "Play"
            if play_rect.collidepoint(mouse_pos):
                update_database()
                selector.show_saved_tracks()
                mid = MidiFile()
                track = MidiTrack()
                mid.tracks.append(track)
                time_old, time_new = time.time(), 0
                track.append(MetaMessage('set_tempo', tempo=bpm2tempo(TEMPO)))
                selector = TrackSelector()
            if exit_rect.collidepoint(mouse_pos):
                print('Close app...')
                os._exit(0)
            # Обработка события нажатия на кнопку "Save"
            if save_rect.collidepoint(mouse_pos):
                print('Saving the song...')
                update_database()
                track_name = generate_next_filename()
                mid.save(track_name)
                add_track_to_database(track_name)
                mid = MidiFile()
                track = MidiTrack()
                mid.tracks.append(track)
                time_old, time_new = time.time(), 0
                track.append(MetaMessage('set_tempo', tempo=bpm2tempo(TEMPO)))
                selector = TrackSelector()

    draw_piano()