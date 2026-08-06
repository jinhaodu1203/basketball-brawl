"""2D Basketball Brawl 程序入口。"""

import os
import pygame

from constants import SCREEN_WIDTH, SCREEN_HEIGHT
from game import play_session


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Basketball Brawl")

    font = pygame.font.SysFont(None, 30)
    small_font = pygame.font.SysFont(None, 20)
    title_font = pygame.font.SysFont(None, 48)
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")

    while True:
        play_session(screen, font, small_font, title_font, assets_dir)


if __name__ == "__main__":
    main()
