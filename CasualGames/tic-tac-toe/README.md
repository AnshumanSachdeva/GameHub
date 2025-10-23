# Tic Tac Toe

Modern Tic-Tac-Toe built with HTML, CSS and JavaScript. Place it inside the `CasualGames/tic-tac-toe` folder. Open `index.html` in a browser to play.

Features
- Responsive modern UI
- Two-player local play
- Score tracking between rounds
- Restart button
 - Single-player mode vs AI (easy / medium / hard)
 - Reset Scores button
 - Improved accessibility: keyboard controls, focus outlines, ARIA live region for results
 - Confetti celebration on win/draw

How to run
1. Open `index.html` in any modern browser (Chrome, Edge, Firefox, Safari).
2. Click any cell to place a mark. Players alternate turns (X starts).
3. Use the Restart button to reset the board (scores persist). To reset scores as well, refresh the page.

Single-player (AI)
- Choose "Single-player" in the mode controls. Human plays as X and AI as O.
- Difficulty options:
	- Easy: random moves.
	- Medium: tries to win and blocks immediate threats, otherwise random.
	- Hard: uses minimax for optimal play.

Accessibility
- Use Tab/Shift+Tab to move focus between cells and controls.
- Use arrow keys (← ↑ → ↓) to move between cells and Enter/Space to make a move.
- Results are announced via an ARIA live region for screen readers.

Notes
- This is a lightweight client-side game — no server required.
- Future improvements: theme selector, animated win line.
