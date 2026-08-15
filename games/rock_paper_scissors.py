import random


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


ASCII_ART = {
    "rock": [
        "    _______      ",
        "---'   ____)     ",
        "      (_____)    ",
        "      (_____)    ",
        "      (____)     ",
        "---.__(___)      ",
    ],
    "paper": [
        "    _______      ",
        "---'   ____)____ ",
        "          ______) ",
        "          _______)",
        "         _______)",
        "---.__________)  ",
    ],
    "scissors": [
        "    _______      ",
        "---'   ____)____ ",
        "          ______) ",
        "       __________)",
        "      (____)     ",
        "---.__(___)      ",
    ],
}


def rock_paper_scissors():
    user_score = 0
    computer_score = 0
    tie_score = 0
    winning_moves = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    game_over = False

    print("\nI'm about to whip your ass at rock paper scissors!")
    print("Shoot on 3..\n1..2..3..shoot!")

    def print_battle(user_shot, choice_to_beat):
        user_lines = ASCII_ART[user_shot]
        computer_lines = ASCII_ART[choice_to_beat]

        print(f"{CYAN}{'-' * 45}{RESET}")
        print(
            f"\n{GREEN}{BOLD}       YOU{RESET}"
            f"                    {CYAN}{BOLD}COMPUTER{RESET}"
        )

        for user_line, computer_line in zip(user_lines, computer_lines):
            print(f"{GREEN}{user_line}{RESET}    vs    {CYAN}{computer_line}{RESET}")
        print()

    while not game_over:
        choice_to_beat = random.choice(["rock", "paper", "scissors"])
        user_shot = input("\nYour move (rock/paper/scissors/(q)uit: ").strip().lower()
        if user_shot == "q":
            break
        if user_shot not in ["rock", "paper", "scissors", "q"]:
            print("You sure you spelled that correctly?")
            continue

        print_battle(user_shot, choice_to_beat)

        print(
            f"\nYou threw: {GREEN}{user_shot.upper()}{RESET}\n"
            f"vs\nMine: {CYAN}{choice_to_beat.upper()}{RESET}\n"
        )
        try:
            if user_shot == choice_to_beat:
                print(f"{YELLOW} 🤝 It's a tie.{RESET}")
                tie_score += 1
            elif winning_moves.get(user_shot) == choice_to_beat:
                print(f"{GREEN}Nice shot!{RESET}")
                user_score += 1
            else:
                print(f"{RED}Ha! I gotcha!{RESET}")
                computer_score += 1

        except ValueError:
            print("Please enter a valid choice.")

        print(f"\n{BOLD}{'─' * 33}{RESET}")
        print(
            f"Scores: {GREEN}You: {user_score}{RESET} | "
            f"{CYAN}Me: {computer_score}{RESET} | "
            f"{YELLOW}Ties: {tie_score}{RESET}"
        )
        print(f"{BOLD}{'─' * 33}{RESET}")

        if user_score == 2:
            print("\n🎉 You won best 2 out of 3. Congrats!")
            game_over = True

        elif computer_score == 2:
            print("\n🤖 Told ya I'd win best 2 out of 3!")
            game_over = True

    play_again = input("\nWanna play again? (y/n): ").lower()
    if play_again == "y":
        rock_paper_scissors()
    else:
        print("That was fun, see ya next time you get bored!")


rock_paper_scissors()
