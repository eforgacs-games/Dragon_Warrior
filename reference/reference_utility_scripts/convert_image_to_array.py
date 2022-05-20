import glob
import os

import cv2
import numpy as np

"""This script converts an image of a Dragon Warrior map to a list of lists containing integers corresponding to each tile."""

SINGLE_TILE_SIZE = 16
floor_tile_key = {
    'ROOF': 0,
    'WALL': 1,
    'WOOD': 2,
    'BRICK': 3,
    'TREASURE_BOX': 4,
    'DOOR': 5,
    'BRICK_STAIR_DOWN': 6,
    'BRICK_STAIR_UP': 7,
    'BARRIER': 8,
    'WEAPON_SIGN': 9,
    'INN_SIGN': 10,
    'CASTLE': 11,
    'TOWN': 12,
    'GRASS': 13,
    'TREES': 14,
    'HILLS': 15,
    'MOUNTAINS': 16,
    'CAVE': 17,
    'GRASS_STAIR_DOWN': 18,
    'SAND': 19,
    'MARSH': 20,
    'BRIDGE': 21,
    'WATER': 22,
    'BOTTOM_COAST': 23,
    'BOTTOM_LEFT_COAST': 24,
    'LEFT_COAST': 25,
    'TOP_LEFT_COAST': 26,
    'TOP_COAST': 27,
    'TOP_RIGHT_COAST': 28,
    'RIGHT_COAST': 29,
    'BOTTOM_RIGHT_COAST': 30,
    'BOTTOM_TOP_LEFT_COAST': 31,
    'BOTTOM_TOP_RIGHT_COAST': 32
}


def create_output_file(output_file):
    with open(f"output/{output_file.split('.png')[0]}.py", 'w') as outfile:
        outfile.write(f"self.{output_file} = [\n")
        for item in dragon_warrior_map_array:
            outfile.write(f"    {item},\n")
        outfile.write("]\n")
    print(dragon_warrior_map_array)


def count_tiles():
    for tile, tile_number in floor_tile_key.items():
        print(f'{tile} count: {sum(x.count(tile_number) for x in dragon_warrior_map_array)}')


# overworld_map = cv2.imread('C:\\Users\\eddie\\PycharmProjects\\Sandbox\\administrative_scripts\\alefgard.png')
project_dir = 'C:\\Users\\eddie\\PycharmProjects\\DragonWarrior\\'
reference_images_dir = f'{project_dir}reference\\reference_images\\'
maps_dir = os.path.join(reference_images_dir, 'maps')
individual_tiles_dir = os.path.join(reference_images_dir, 'individual_tiles')


def perform_conversion(map_array, filename):
    try:
        assert image_to_convert_rgb.shape[0] % SINGLE_TILE_SIZE == 0
        assert image_to_convert_rgb.shape[1] % SINGLE_TILE_SIZE == 0
    except AssertionError as e:
        print(f"{filename} AssertionError: {e}")
    match_tiles(filename, map_array)
    # count_tiles()
    with open(f"output/output.py", 'a') as outfile:
        outfile.write(f"self.{filename.split('.png')[0]} = [\n")
        for item in map_array:
            outfile.write(f"    {item},\n")
        outfile.write("]\n")
    print(map_array)


def match_tiles(filename, map_array):
    for individual_tile_file in glob.glob(os.path.join(individual_tiles_dir, '*.png')):
        # filename = os.path.join(individual_tiles_path, '12.png') # village
        template = cv2.imread(individual_tile_file)
        w, h = template.shape[:-1]
        res = cv2.matchTemplate(image_to_convert_rgb, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):  # Switch columns and rows
            column = pt[0] // SINGLE_TILE_SIZE
            row = pt[1] // SINGLE_TILE_SIZE
            try:
                map_array[row][column] = int(os.path.basename(individual_tile_file).strip('.png'))
            except IndexError as e:
                print(f"{filename} IndexError: {e}")
                print(f"Max row is {len(map_array)}, attempted {row}")
                print(f"Max column is {len(map_array[0])}, attempted {column}")
                continue
        # match_tile(template, int(os.path.basename(file).strip('.png')), image_to_convert_rgb, map_array)
        # cv2.imwrite('result.png', overworld_map)


# for batch conversions, use this for loop
# for map_filename in os.listdir(maps_dir):

# for single conversions, use this variable
map_filename = 'staff_of_rain_cave.png'

image_to_convert_rgb = cv2.imread(os.path.join(maps_dir, map_filename))
# image_to_convert_gray = cv2.cvtColor(image_to_convert_rgb, cv2.COLOR_BGR2GRAY)
image_tile_width = image_to_convert_rgb.shape[0] // SINGLE_TILE_SIZE  # 124 for alefgard.png
image_tile_height = image_to_convert_rgb.shape[1] // SINGLE_TILE_SIZE
dragon_warrior_map_array = [[floor_tile_key['GRASS']] * image_tile_height for i in range(image_tile_width)]
perform_conversion(dragon_warrior_map_array, map_filename)
    # create_output_file(map_filename)
    # print(DataFrame(overworld_map_array))
