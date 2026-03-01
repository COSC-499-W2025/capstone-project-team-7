# COSC322 Amazons Project

This project implements the board game *Amazons* using a combination of Monte Carlo Tree Search (MCTS) and heuristic evaluation to decide moves. Two players, White and Black, take turns moving one of their queens and then firing an arrow that permanently blocks a square on the board. The game ends when the active player has no legal moves, at which point that player loses and the opponent wins.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Game Rules and Flow](#game-rules-and-flow)
4. [Monte Carlo Tree Search (MCTS)](#monte-carlo-tree-search-mcts)
    - [Selection and UCB](#selection-and-ucb)
    - [Expansion, Rollout, and Backpropagation](#expansion-rollout-and-backpropagation)
5. [Heuristic Evaluation](#heuristic-evaluation)
6. [GUI Integration and Room Management](#gui-integration-and-room-management)
7. [Win/Loss Detection and Termination](#winloss-detection-and-termination)
8. [Running the Project](#running-the-project)
9. [Future Enhancements](#future-enhancements)

---

## Overview

The COSC322 Amazons Project simulates the game of Amazons. Each turn, a player:
- **Moves a Queen:** Like a chess queen, along any straight or diagonal line, if the path is clear.
- **Fires an Arrow:** From the queen’s new position, shooting in any straight or diagonal line to block a square.

Queens are never removed from the board; they simply become immobilized when blocked. The game ends when the current player has no legal moves. The project uses MCTS combined with heuristics to plan moves and includes a GUI that handles room management (auto-joining the first room with the option to switch manually).

---

## Project Structure

- **COSC322Test.java**  
  Main game player class. Handles server connection, room joining, and game logic. It auto-joins the first available room and updates the GUI with available rooms. It processes game messages, invokes MCTS for moves, and handles win/lose messages.

- **TreeNode.java**  
  Represents a node in the MCTS tree. Contains the board state, the move that led to that state, children, visit counts, and cumulative rewards. It includes methods for node expansion and terminal state detection.

- **MonteCarlo.java**  
  Implements MCTS. Handles tree traversal using the UCB score, node expansion, rollout (both random and heuristic), and backpropagation. It selects the best move based on UCB scores after many iterations.

- **HeuristicEvaluator.java**  
  Evaluates board states using metrics like minimum distances and mobility. It combines these metrics using weighted functions and normalizes the result with a sigmoid function.

- **AmazonsUtility.java**  
  Provides helper methods to generate a mobility map, print the board, validate moves, and perform a sigmoid transformation.

- **AmazonsActionFactory.java**  
  Generates all legal moves for a given board state and player color using directional arrays to iterate through queen moves and arrow moves.

- **AmazonsAction.java**  
  Encapsulates a move in the game (queen movement plus arrow shot) and includes methods to apply moves to the board state and update the mobility map.

---

## Game Rules and Flow

### Game Rules

- **Setup:**  
  Each player starts with four queens in fixed positions.

- **Turn Mechanics:**  
  1. Move a queen in any straight or diagonal direction.
  2. From the new queen position, fire an arrow in any straight or diagonal direction to block a square.
  
- **End Condition:**  
  The game ends when the player whose turn it is has no legal moves available. That player loses, and the opponent wins.

### Flow in the Code

- **Connection and Room Joining:**  
  The `COSC322Test` class connects to the game server, retrieves available rooms, auto-joins the first room, and updates the GUI with room information. The GUI also allows the user to click on a different room to join.

- **Gameplay:**  
  Game messages are received (including board states and moves) and processed. The MCTS engine computes moves, and the GUI is updated accordingly.

- **Terminal States:**  
  When no legal moves are available, the code prints “You lose” on the losing client and (with modifications) “You win” on the winning client. The program then stops execution using `System.exit(0)`.

---

## Monte Carlo Tree Search (MCTS)

MCTS is used to evaluate many possible future moves. It consists of four main steps:

### Selection and UCB

- **Selection:**  
  Starting at the root node, the algorithm selects child nodes based on the highest Upper Confidence Bound (UCB) score.
  
- **UCB Score:**  
  The UCB score for a node is given by:
  
  \[
  \text{UCB} = \frac{Q}{N} + c \sqrt{\frac{\ln N_p}{N}}
  \]
  
  Where:  
  - \( Q \) is the cumulative reward (sum of outcomes).  
  - \( N \) is the number of visits to the node.  
  - \( N_p \) is the number of visits to the parent node.  
  - \( c \) is the exploration coefficient.
  
  The first term (\(\frac{Q}{N}\)) is the exploitation term, reflecting the average reward. The second term (\( c \sqrt{\frac{\ln N_p}{N}} \)) is the exploration term, favoring nodes that have been less visited.

### Expansion, Rollout, and Backpropagation

- **Expansion:**  
  When a leaf node (with unexplored moves) is reached, it is expanded by generating one or more child nodes.
  
- **Rollout:**  
  From the new node, a simulation (rollout) is executed to a terminal state. This can be either a fully random simulation or one guided by the heuristic evaluator.
  
- **Backpropagation:**  
  The result of the rollout is then propagated back up the tree, updating the visit count and total reward for each node along the path.

After running many iterations, the action associated with the child node having the highest average reward is chosen.

---

## Heuristic Evaluation

Heuristic evaluation helps guide MCTS by providing a fast estimate of a board state's value.

- **Distance Metrics:**  
  The evaluator computes metrics such as the minimum distance from each square to the nearest queen. This reflects board control.
  
- **Mobility Map:**  
  A mobility map is generated to indicate the number of free adjacent squares from each board cell. Higher mobility usually correlates with a better position.
  
- **Weighting Functions:**  
  Several functions (e.g., \(f1\), \(f2\), etc.) weight these metrics and combine them into a single score. The resulting heuristic is normalized using a sigmoid function.
  
- **Interpretation:**  
  A positive heuristic indicates an advantage for White; a negative value indicates an advantage for Black. This heuristic guides the rollout phase in MCTS.

---

## GUI Integration and Room Management

The project uses a GUI (based on the provided `BaseGameGUI` class) to:

- **Display the Game Board:**  
  The GUI shows the board, queen positions, arrow placements, and current game state.
  
- **Room Management:**  
  When the user logs in, the `COSC322Test` class retrieves a list of available rooms, auto-joins the first one, and updates the GUI with the complete list. The method `joinRoom(String roomName)` is available so that the user can click on another room to join it.

- **User Interaction:**  
  The GUI allows manual room switching while the game is running. When the user clicks on a different room, the GUI calls `joinRoom()` to switch rooms accordingly.

---

## Win/Loss Detection and Termination

- **Terminal State:**  
  A terminal state is defined as the point when the current player has no legal moves. The `TreeNode` class checks for terminal states by determining whether there are any legal moves left.
  
- **Message Handling:**  
  The server or game logic will trigger a message like `"cosc322.game-state.userlost"` on the client that loses. The code prints “You lose” for the losing client.
  
- **Win Message:**  
  To balance this, a “You win” message can be added on the winning client. This can be achieved by checking (after the opponent’s move) if the opponent has no legal moves left. In that case, the winning client prints “You win” and calls `System.exit(0)` to stop execution.
  
- **Termination:**  
  Once a win or loss is detected, the program immediately stops further processing by invoking `System.exit(0)`, ensuring that the win/lose message is the final output.

---

## Running the Project

### Requirements

- **Java Version:** JDK 17 or compatible.
- **Libraries:** SmartFox server/client libraries and the BaseGameGUI components from `ygraph.ai.smartfox.games`.
- **IDE/Environment:** Use an IDE (e.g., Eclipse) or compile and run from the command line.

### Steps

1. **Compile the Code:**  
   Ensure all source files (e.g., `COSC322Test.java`, `TreeNode.java`, `MonteCarlo.java`, etc.) are compiled.

2. **Run the Main Class:**  
   Launch `COSC322Test` with the appropriate command-line arguments for username and password. For example:
