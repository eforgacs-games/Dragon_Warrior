from src.common import play_sound, confirmation_sfx


def prompt_for_save(player):
    # TODO(ELF): Implement this dialog logic along with game saving.
    deeds = input("Will thou tell me now of thy deeds so they won't be forgotten?").lower().strip()
    play_sound(confirmation_sfx)
    if deeds == "y":
        print("Thy deeds have been recorded on the Imperial Scrolls of Honor.")
    continuing = input("Dost thou wish to continue thy quest?").lower().strip()
    play_sound(confirmation_sfx)
    if continuing == "y":
        print(f"Goodbye now, {player.name}.\n'Take care and tempt not the Fates.")
    elif continuing == "N":
        print("Rest then for awhile.")
