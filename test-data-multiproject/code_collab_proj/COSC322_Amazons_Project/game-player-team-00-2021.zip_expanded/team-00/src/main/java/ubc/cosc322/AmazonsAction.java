package ubc.cosc322;

public class AmazonsAction {
    // yields for the queen’s start and end positions and the arrow’s destination
    public int queenSrcX, queenSrcY, queenDestX, queenDestY, arrowDestX, arrowDestY;

    // constructor: initializes the move with given coordinates
    public AmazonsAction(int queenSrcX, int queenSrcY, int queenDestX, int queenDestY, int arrowDestX, int arrowDestY) {
        this.queenSrcX = queenSrcX;
        this.queenSrcY = queenSrcY;
        this.queenDestX = queenDestX;
        this.queenDestY = queenDestY;
        this.arrowDestX = arrowDestX;
        this.arrowDestY = arrowDestY;
    }

    // applies the complete move (queen move plus arrow shot) to the provided state,
    // returns a new state: [updated board, updated mobility map]
    public static int[][][] applyAction(AmazonsAction action, int[][][] state) {
        int size = 10;
        int[][] board = state[0];
        int[][] mobilityMap = state[1];

        // deep copies of the board and mobility map
        int[][] newBoard = copy2DArray(board, size);
        int[][] newMobility = copy2DArray(mobilityMap, size);

        //	 Move the queen from its source to destination
        newBoard[action.queenDestY][action.queenDestX] = board[action.queenSrcY][action.queenSrcX];
        newBoard[action.queenSrcY][action.queenSrcX] = 0;
        //Fire the arrow (represented by 3)
        newBoard[action.arrowDestY][action.arrowDestX] = 3;

        // Adjust mobility around affected spots
        // Where the queen left, mobility goes up
        updateMobility(newMobility, action.queenSrcY, action.queenSrcX, +1);
        // Where the queen lands, mobility is reduced
        updateMobility(newMobility, action.queenDestY, action.queenDestX, -1);
        // and the same here, the arrow landing reduces mobility
        updateMobility(newMobility, action.arrowDestY, action.arrowDestX, -1);

        return new int[][][]{newBoard, newMobility};
    }

    // Apply only a queen move (ignoring arrow placement) and return a new board state
    public static int[][] applyQueenMove(int queenSrcX, int queenSrcY, int queenDestX, int queenDestY, int[][][] state) {
        int size = 10;
        int[][] board = state[0];
        int[][] newBoard = copy2DArray(board, size);
        newBoard[queenDestY][queenDestX] = board[queenSrcY][queenSrcX];
        newBoard[queenSrcY][queenSrcX] = 0;
        return newBoard;
    }

    // Check if this action is equal to another action, all coordinates match
    public boolean isEqual(AmazonsAction other) {
        return (this.queenSrcX == other.queenSrcX &&
                this.queenSrcY == other.queenSrcY &&
                this.queenDestX == other.queenDestX &&
                this.queenDestY == other.queenDestY &&
                this.arrowDestX == other.arrowDestX &&
                this.arrowDestY == other.arrowDestY);
    }

    public void printMove() {
        System.out.println(queenSrcX + ", " + queenSrcY + " -> " +
                           queenDestX + ", " + queenDestY + " ; arrow: " +
                           arrowDestX + ", " + arrowDestY);
    }

    private static int[][] copy2DArray(int[][] array, int size) {
        int[][] copy = new int[size][size];
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                copy[i][j] = array[i][j];
            }
        }
        return copy;
    }

    // Update the mobility map around a given cell by adding the specified delta
    // check all 8 adjacent cells for possible moves
    private static void updateMobility(int[][] mobilityMap, int centerY, int centerX, int delta) {
        for (int[] d : AmazonsUtility.DIRECTIONS) {
            int newY = centerY + d[0];
            int newX = centerX + d[1];
            if (AmazonsUtility.isSpotValid(newY, newX)) {
                mobilityMap[newY][newX] += delta;
            }
        }
    }
}