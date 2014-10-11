import pygame

class sound():
    def __init__(self, n):
        pygame.mixer.init(44100, -16, 2, 2048)
        PATH = "tools/sounds/"
        self.cor = pygame.mixer.Sound(PATH + n)

    def play(self):
        self.cor.play()
