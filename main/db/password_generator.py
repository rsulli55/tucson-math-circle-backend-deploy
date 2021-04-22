import random

ANIMAL_LIST = ["dog", "cat", "dolphin", "snake", "fish", "bird", "lizard,"]
COLOR_LIST = ["red", "blue", "green", "yellow", "orange", "purple", "pink"]


def generate_random_password():
    animal_num = random.randint(0, len(ANIMAL_LIST) - 1)
    color_num = random.randint(0, len(COLOR_LIST) - 1)
    return COLOR_LIST[color_num] + ANIMAL_LIST[animal_num]
