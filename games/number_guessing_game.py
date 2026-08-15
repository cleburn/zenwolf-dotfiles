import random


def guess_number_game():
    number_to_guess = random.randint(1, 100)
    attempts = 0
    guessed_correctly = False

    print("Welcome to the Number Guessing Game!")
    print("I'm thinking of a number between 1 and 100. Can you guess it?")

    while not guessed_correctly:
        try:
            user_guess = int(input("Enter your guess: "))
            attempts += 1

            if user_guess < number_to_guess:
                print("Too low! Try again.")
            elif user_guess > number_to_guess:
                print("Too high! Try again.")
            else:
                print(
                    f"🎉 Congratulations! You guessed the number in "
                    f"{attempts} tries!"
                )
                guessed_correctly = True
        except ValueError:
            print("⚠️ Please enter a valid number.")

    play_again = input("Do you want to play again? (y/n): ").lower()
    if play_again == "y":
        guess_number_game()
    else:
        print("Thanks for playing! Adios!")


guess_number_game()
