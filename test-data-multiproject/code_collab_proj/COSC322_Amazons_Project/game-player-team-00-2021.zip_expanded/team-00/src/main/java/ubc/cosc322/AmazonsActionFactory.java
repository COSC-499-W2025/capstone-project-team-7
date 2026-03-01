package ubc.cosc322;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.Queue;

public class AmazonsActionFactory {
    // returns all possible moves (queen move + arrow shot) for the specified color given the board state
    public static ArrayList<AmazonsAction> getActions(int[][][] state, int color) {
        int size = 10;
        int[][] board = state[0];
        ArrayList<AmazonsAction> allActions = new ArrayList<>();

        // collect queen positions for the specified color
        Queue<int[]> queenPositions = new LinkedList<>();
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                if (board[i][j] == color) {
                    queenPositions.add(new int[] { i, j });
                }
            }
        }

        // for every queen, try moving in all eight directions
        while (!queenPositions.isEmpty()) {
            int[] queenPos = queenPositions.poll();
            int queenSrcY = queenPos[0];
            int queenSrcX = queenPos[1];

            for (int[] dir : AmazonsUtility.DIRECTIONS) {
                //move step by step in the current direction
                for (int d = 1; d < size; d++) {
                    int queenDestY = queenSrcY + d * dir[0];
                    int queenDestX = queenSrcX + d * dir[1];
                    if (AmazonsUtility.isSpotValid(board, queenDestY, queenDestX)) {
                        //for each valid queen move, generate all possible arrow moves
                        allActions.addAll(getArrowMoves(queenSrcX, queenSrcY, queenDestX, queenDestY, state));
                    } else {
                        break;
                    }
                }
            }
        }
        return allActions;
    }

    // given a queen move (from queenSrc to queenDest), returns all arrow moves possible
    private static ArrayList<AmazonsAction> getArrowMoves(int queenSrcX, int queenSrcY, int queenDestX, int queenDestY, int[][][] state) {
        int size = 10;
        ArrayList<AmazonsAction> arrowMoves = new ArrayList<>();
        // get board state after moving the queen
        int[][] boardAfterQueen = AmazonsAction.applyQueenMove(queenSrcX, queenSrcY, queenDestX, queenDestY, state);

        // try shooting an arrow in every direction from the queen's new position to see best move
        for (int[] dir : AmazonsUtility.DIRECTIONS) {
            for (int d = 1; d < size; d++) {
                int arrowDestY = queenDestY + d * dir[0];
                int arrowDestX = queenDestX + d * dir[1];
                if (AmazonsUtility.isSpotValid(boardAfterQueen, arrowDestY, arrowDestX)) {
                    arrowMoves.add(new AmazonsAction(queenSrcX, queenSrcY, queenDestX, queenDestY, arrowDestX, arrowDestY));
                } else {
                    break;
                }
            }
        }
        return arrowMoves;
    }
}