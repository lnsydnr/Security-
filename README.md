# Security+ Study App

A Qt desktop application to help you study for the CompTIA Security+ exam.

The app stores data locally in your home directory at `~/.security_plus_study_app/study.db` and includes:

- Flashcards with simplified spaced repetition scheduling
- CSV / JSON question import support
- Inline quiz mode with multiple-choice and free-form questions
- Per-question quiz results and explanations
- Quiz history tracking with answer review
- Dashboard stats and optional progress charting

## Project Structure

- `src/security_app.py` — app launcher
- `src/gui.py` — main GUI and tab logic
- `src/app_core.py` — database helpers, import logic, flashcard scheduling, and quiz tracking
- `requirements.txt` — Python dependencies
- `assets/` — app icons and static assets
- `data/example_questions/` — sample question files

## Database Schema
- `questions` table: stores all questions with fields for domain, question text, answer, options, and explanation
- `flashcards` table: tracks flashcard scheduling with fields for question ID, next review date, and performance history
- `quizzes` table: records quiz attempts with fields for timestamp, domain, question count, and score
- `quiz_answers` table: stores individual quiz question answers with fields for quiz ID, question ID, user answer, correctness, and explanation
- `attempts` table: tracks quiz attempts with fields for timestamp, domain, question count, and score

## Requirements

- Python 3.8+
- `PySide6` for the GUI
- `matplotlib` is optional for dashboard charts

## Installation

- Clone the repository:
  ```sh
  git clone https://github.com/lnsydnr/Security-Plus-App.git
  cd Security-Plus-App
  ```
- Install dependencies:
  ```sh
  python -m pip install -r requirements.txt
  ```

## Running the App

From the repository root, launch the app from the `src` directory:

```sh
cd src
python security_app.py
```

## App Tabs

- **Dashboard**: overview of quiz accuracy by domain with interactive bar chart showing value labels and refreshable stats
- **Flashcards**: review due flashcards and grade them to update scheduling; track easy and hard cards across sessions for focused studying
- **Question Bank**: browse and delete stored questions
- **Quiz**: select domain and question count, answer inline, and see results
- **History**: review past quiz attempts and detailed answer breakdowns
- **Import**: load questions from CSV or JSON files
- **Settings**: export question bank, auto-assign missing domains, and reset the local database

## Flashcard Categories

The flashcards system automatically categorizes your cards based on performance:

- **Due Flashcards**: Cards scheduled for review based on the spaced repetition algorithm
- **Easy Cards**: Cards you've graded as "Easy" (quality 5) - cards you've mastered
- **Hard Cards**: Cards you've graded as "Hard" (quality 4) - cards that need more practice

Your card categories are saved automatically and persist across sessions, allowing you to focus on weak areas or revisit mastered content as needed.

## Automatic Domain Assignment

The app now infers missing domains using CompTIA Security+ objective keyword patterns. This happens automatically during CSV/JSON import when a domain is not supplied, and you can also run a batch reassignment from **Settings** using **Add Domains to Missing Questions**.

## Import Formats

### CSV

Supported CSV fields include:

- `domain` (optional; missing values are inferred)
- `question`
- `answer`
- `type`
- `option a`
- `option b`
- `option c`
- `option d`
- `explanation`

Example:

```csv
domain,question,option a,option b,option c,option d,answer,explanation
Network Security,Which protocol is used to securely transfer files over a network?,FTP,SFTP,Telnet,SMTP,SFTP,SFTP uses SSH to securely transfer files.
```

### JSON

Each item should include:

- `domain` (optional; missing values are inferred)
- `question`
- `answer`
- `options` (for MCQs)
- `explanation`

Example:

```json
[
  {
    "domain": "Network Security",
    "question": "Which protocol is used to securely transfer files over a network?",
    "options": ["FTP", "SFTP", "Telnet", "SMTP"],
    "answer": "SFTP",
    "explanation": "SFTP uses SSH to securely transfer files."
  }
]
```

The **Import** tab also includes **Convert Questions File to Import Format...**, which normalizes CSV or JSON question files into the import-ready JSON structure.

## Exporting Questions

Use the **Settings** tab and click **Export Question Bank (JSON)** to save all stored questions.

## Resetting the Database

Use the **Settings** tab and click **Reset Database (delete all)** to remove all questions, flashcards, attempts, quizzes, and progress.

## Notes

- Quiz answers are stored in the local SQLite database for history and statistics.
- Flashcard scheduling uses a simplified SM-2-like algorithm with three grading levels: Hard (4), Easy (5), and Mastered (6).
- The dashboard displays an interactive bar chart showing accuracy by domain, with value labels for quick reference.
- The app supports both multiple-choice and free-form questions.
- Easy and hard flashcard categorizations are persisted in `~/.security_plus_study_app/flashcards/.known_cards.json`.

## Uninstall
To uninstall, simply delete the executable or the repository (if cloned locally) and remove the local data directory at `~/.security_plus_study_app/`.

Windows:
```powershell
Remove-Item -Recurse -Force ~/.security_plus_study_app/
```
Linux/Mac:
```bash
rm -rf ~/.security_plus_study_app/
```

## License

MIT License. See [LICENSE](LICENSE) for details.
