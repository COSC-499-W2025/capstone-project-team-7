package ubc.cosc322;

public class AmazonsUtility {

    // helper array of 8 direction offsets: up, up-left, left, down-left, down, down-right, right,up-right
    public static final int[][] DIRECTIONS = {
        {-1,  0},  // up
        {-1, -1},  // up-left
        { 0, -1},  // left
        { 1, -1},  // down-left
        { 1,  0},  // down
        { 1,  1},  // down-right
        { 0,  1},  // right
        {-1,  1}   // up-right
    };

    // Returns a mobility map (as a 10x10 grid) indicating how many directions are available	
    // from each square on the board (only counts if the adjacent spot is valid).
    public static int[][] getMobilityMap(int[][] board) {
        int size = 10;
        int[][] mobilityMap = new int[size][size];
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                mobilityMap[i][j] = 0;
                // loop through all 8 possible directions
                for (int[] dir : DIRECTIONS) {
                    int newY = i + dir[0];
                    int newX = j + dir[1];
                    if (isSpotValid(board, newY, newX)) {
                        mobilityMap[i][j]++;
                    }
                }
            }
        }
        return mobilityMap;
    }

    // Nicely prints the board with a border. Displays a space for 0, 'X' for 3, and the number otherwise
    public static void printBoard(int[][] board) {
        int size = 10;
        String line = "-----------------------------------------";
        System.out.println(line);
        for (int i = 0; i < size; i++) {
            System.out.print("| ");
            for (int j = 0; j < size; j++) {
                char c;
                if (board[i][j] == 0) {
                    c = ' ';
                } else if (board[i][j] == 3) {
                    c = 'X';
                } else {
                    c = Character.forDigit(board[i][j], 10);
                }
                System.out.print(c + " | ");
            }
            System.out.println("\n" + line);
        }
        System.out.println();
    }

    //see if the coordinates (y, x) are within board boundaries.
    public static boolean isSpotValid(int y, int x) {
        return x >= 0 && x < 10 && y >= 0 && y < 10;
    }

    //check if the coordinates (y, x) are within bounds AND the board's spot is empty, = 0
    public static boolean isSpotValid(int[][] board, int y, int x) {
        return isSpotValid(y, x) && board[y][x] == 0;
    }

    //  basic sigmoid function that squashes input values. The divisor (5) softens the steepness
    public static double sigmoid(double x) {
        return 1 / (1 + Math.exp(-x / 5));
    }
}