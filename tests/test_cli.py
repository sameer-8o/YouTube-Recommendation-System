"""Exercise the recommendation assistant through real command-line sessions.

Run from the repository root with:
    python -m unittest discover -s tests -v

Each test launches a fresh process, sends user answers, and checks observable
behavior. No external packages or network access are needed.
"""

from pathlib import Path
import subprocess
import sys
import unittest


PROGRAM = Path(__file__).resolve().parents[1] / "youtube_recommendation_assistant.py"
MENU_PROMPT = "Choose an option (1-7): "
TIME_PROMPT = "How many minutes do you have? (5-120): "
SAVE_PROMPT = "Add one video to Watch Later? 1 = Yes, 2 = No: "
VIDEO_PROMPT = "Enter the video number to save: "


class RecommendationCliTests(unittest.TestCase):
    def run_cli(self, *answers):
        """Run a session and require a normal exit without a traceback."""
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(PROGRAM)],
            input="\n".join(answers) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("Thank you for using", result.stdout)
        return result.stdout

    def assert_retries(self, output, prompt, rejected_count):
        """Require feedback and another prompt for every rejected answer."""
        parts = output.split(prompt)
        self.assertEqual(len(parts) - 1, rejected_count + 1)
        for feedback in parts[1:-1]:
            self.assertTrue(feedback.strip(), "Rejected input needs an explanation")

    def test_startup_catalog_and_exit(self):
        output = self.run_cli("7")
        self.assertIn("Videos loaded: 30", output)

    def test_empty_and_malformed_menu_answers_are_retried(self):
        for invalid in ("", "   ", "abc", "2.5", "-1"):
            with self.subTest(answer=repr(invalid)):
                output = self.run_cli(invalid, "7")
                self.assert_retries(output, MENU_PROMPT, 1)

    def test_menu_rejects_values_outside_both_bounds(self):
        output = self.run_cli("0", "8", "7")
        self.assert_retries(output, MENU_PROMPT, 2)

    def test_superscript_digit_is_rejected_without_crashing(self):
        # This used to pass str.isdigit(), then crash during int conversion.
        output = self.run_cli("\u00b2", "7")
        self.assert_retries(output, MENU_PROMPT, 1)

    def test_very_long_number_is_rejected_without_crashing(self):
        # Also exceeds Python's default integer-string conversion limit.
        output = self.run_cli("9" * 5000, "7")
        self.assert_retries(output, MENU_PROMPT, 1)

    def test_valid_whitespace_and_arabic_digits_are_accepted(self):
        for answer in ("  7  ", "\u0667"):
            with self.subTest(answer=answer):
                output = self.run_cli(answer)
                self.assert_retries(output, MENU_PROMPT, 0)

    def test_end_of_input_exits_cleanly_at_menu_and_category_prompt(self):
        # Piped input can end before the user selects Exit. Cover EOF at two
        # different prompts without appending the normal exit-menu answer.
        for answers in ("", "1\n"):
            with self.subTest(input=repr(answers)):
                result = subprocess.run(
                    [sys.executable, "-X", "utf8", str(PROGRAM)],
                    input=answers,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn("Input interrupted.", result.stdout)
                self.assertIn("Exiting", result.stdout)

    def test_category_ignores_case_and_surrounding_spaces(self):
        output = self.run_cli("1", "  tEcH  ", "2", "7")
        for title in (
            "Building a Startup in 2026",
            "How AI Is Changing Everyday Apps",
            "Coding a Simple Game in a Weekend",
            "Watch this BEFORE you buy a Camera!",
        ):
            self.assertIn(title, output)
        self.assertNotIn("History of the Ottoman Empire", output)
        self.assertIn("No video added.", output)

    def test_unknown_category_and_mood_return_to_menu(self):
        output = self.run_cli("1", "unknown", "2", "unknown", "7")
        self.assertIn("No videos found in that category.", output)
        self.assertIn("No videos found for that mood.", output)

    def test_mood_results_are_sorted_by_popularity(self):
        output = self.run_cli("2", "  FuNnY  ", "2", "7")
        titles = (
            "Funniest Cat Fails Compilation",
            "Try Not to Laugh Challenge",
            "Awkward First Date Sketches",
            "Stand-Up Comedy Highlights",
        )
        positions = [output.index(title) for title in titles]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Meditation for Beginners", output)

    def test_time_filter_includes_limit_and_sorts_shortest_first(self):
        output = self.run_cli("3", "10", "2", "7")
        titles = (
            "Funniest Cat Fails Compilation",
            "Awkward First Date Sketches",
            "10-Minute Full Body Workout",
            "Meditation for Beginners",
        )
        positions = [output.index(title) for title in titles]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Try Not to Laugh Challenge", output)

    def test_time_filter_accepts_minimum_and_maximum_limits(self):
        output = self.run_cli("3", "5", "3", "120", "2", "7")
        self.assertIn("No videos fit that time limit. Try a higher number.", output)
        self.assertIn("Relaxing Lo-fi Beats to Study", output)
        self.assertIn("Funniest Cat Fails Compilation", output)

    def test_time_filter_retries_empty_malformed_and_out_of_range_answers(self):
        output = self.run_cli("3", "", "abc", "4", "121", "10", "2", "7")
        self.assert_retries(output, TIME_PROMPT, 4)
        self.assertIn("10-Minute Full Body Workout", output)

    def test_watch_later_prevents_duplicates(self):
        output = self.run_cli("1", "Tech", "1", "1", "1", "Tech", "1", "1", "4", "7")
        self.assertIn('"Building a Startup in 2026" added to Watch Later.', output)
        self.assertIn('"Building a Startup in 2026" is already in Watch Later.', output)
        self.assertIn("Total: 1 video(s), 18 minutes of watch time.", output)

    def test_watch_later_totals_multiple_videos(self):
        output = self.run_cli("1", "Tech", "1", "1", "1", "Music", "1", "1", "4", "7")
        self.assertIn('"Building a Startup in 2026" added to Watch Later.', output)
        self.assertIn('"Relaxing Lo-fi Beats to Study" added to Watch Later.', output)
        self.assertIn("Total: 2 video(s), 78 minutes of watch time.", output)

    def test_save_prompt_retries_invalid_answers_then_declines(self):
        output = self.run_cli("1", "Tech", "abc", "0", "3", "2", "4", "7")
        self.assert_retries(output, SAVE_PROMPT, 3)
        self.assertIn("No video added.", output)
        self.assertIn("Your Watch Later list is empty.", output)

    def test_video_selection_retries_invalid_indices_then_saves(self):
        output = self.run_cli("1", "Tech", "1", "0", "5", "2", "4", "7")
        self.assert_retries(output, VIDEO_PROMPT, 2)
        self.assertIn('"How AI Is Changing Everyday Apps" added to Watch Later.', output)
        self.assertIn("Total: 1 video(s), 20 minutes of watch time.", output)

    def test_clearing_can_be_cancelled_then_confirmed(self):
        output = self.run_cli("1", "Tech", "1", "1", "5", "2", "4", "5", "1", "4", "7")
        self.assertIn("Cancelled.", output)
        self.assertIn("Total: 1 video(s), 18 minutes of watch time.", output)
        self.assertIn("Watch Later list cleared.", output)
        self.assertIn("Your Watch Later list is empty.", output)

    def test_clearing_an_empty_list_returns_to_menu(self):
        output = self.run_cli("5", "7")
        self.assertIn("The list is already empty.", output)
        self.assertNotIn("Are you sure?", output)

    def test_watch_later_starts_empty_in_a_new_session(self):
        first_session = self.run_cli("1", "Tech", "1", "1", "4", "7")
        self.assertIn("Total: 1 video(s), 18 minutes of watch time.", first_session)
        second_session = self.run_cli("4", "7")
        self.assertIn("Your Watch Later list is empty.", second_session)

    def test_about_screen_returns_to_menu(self):
        output = self.run_cli("6", "7")
        self.assertIn("ABOUT YOUTUBE AS A DISRUPTIVE INNOVATION", output)
        self.assertIn("Clayton Christensen", output)
        self.assertEqual(output.count(MENU_PROMPT), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
