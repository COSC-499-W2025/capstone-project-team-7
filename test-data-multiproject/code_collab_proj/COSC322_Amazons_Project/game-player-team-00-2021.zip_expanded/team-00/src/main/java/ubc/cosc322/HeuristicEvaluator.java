package ubc.cosc322;

import java.util.LinkedList;
import java.util.Queue;

public class HeuristicEvaluator {
    private static final int WHITE_QUEEN = 1;
    private static final int BLACK_QUEEN = 2;
    private static final double TURN_ADVANTAGE = 0.15;
    private static final int BOARD_SIZE = 10;

    public static double getHeuristicEval(int[][][] state, int playerTurn) {
        int[][] board = state[0];
        int[][] mobilityMap = state[1];

        double[] queenMetrics = calculateQueenDistanceMetrics(board, playerTurn);
        double t1 = queenMetrics[0];
        double c1 = queenMetrics[1];
        double diffWeight = queenMetrics[2];

        double t2 = 0.0, c2 = 0.0, mobilityEval = 0.0;

        if (diffWeight > 10.0) {
            double[] kingMetrics = calculateKingDistanceMetrics(board, playerTurn);
            t2 = kingMetrics[0];
            c2 = kingMetrics[1];
            mobilityEval = evaluateMobility(board, mobilityMap, diffWeight);
        } else {
            diffWeight = 0.0;
        }

        double territoryEval = ((100.0 - diffWeight) / 100.0) * t1
                             + ((1.0 - (100.0 - diffWeight) / 100.0) / 4.0) * (c1 + t2 + c2);
        return territoryEval + mobilityEval;
    }

    private static double[] calculateQueenDistanceMetrics(int[][] board, int playerTurn) {
        int[][] whiteDistances = new int[BOARD_SIZE][BOARD_SIZE];
        int[][] blackDistances = new int[BOARD_SIZE][BOARD_SIZE];
        initializeDistances(whiteDistances);
        initializeDistances(blackDistances);

        propagateDistances(board, whiteDistances, WHITE_QUEEN);
        propagateDistances(board, blackDistances, BLACK_QUEEN);

        double score = 0.0, controlScore = 0.0, diffWeight = 0.0;
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                controlScore += Math.pow(2, -whiteDistances[i][j]) - Math.pow(2, -blackDistances[i][j]);
                if (whiteDistances[i][j] != Integer.MAX_VALUE && blackDistances[i][j] != Integer.MAX_VALUE) {
                    diffWeight += Math.pow(2, -Math.abs(whiteDistances[i][j] - blackDistances[i][j]));
                }
                if (whiteDistances[i][j] < blackDistances[i][j]) {
                    score += 1.0;
                } else if (whiteDistances[i][j] > blackDistances[i][j]) {
                    score -= 1.0;
                } else if (whiteDistances[i][j] != Integer.MAX_VALUE) {
                    score += (playerTurn == WHITE_QUEEN ? TURN_ADVANTAGE : -TURN_ADVANTAGE);
                }
            }
        }
        return new double[]{score, 2.0 * controlScore, diffWeight};
    }

    private static void initializeDistances(int[][] distances) {
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                distances[i][j] = Integer.MAX_VALUE;
            }
        }
    }

    private static void propagateDistances(int[][] board, int[][] distances, int queenType) {
        Queue<int[]> queue = new LinkedList<>();
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                if (board[i][j] == queenType) {
                    queue.add(new int[]{i, j});
                    distances[i][j] = 0;
                }
            }
        }

        int[][] directions = {
            {-1, 0}, {-1, -1}, {0, -1}, {1, -1},
            {1, 0}, {1, 1}, {0, 1}, {-1, 1}
        };

        while (!queue.isEmpty()) {
            int[] pos = queue.poll();
            int posY = pos[0], posX = pos[1];
            int nextDist = distances[posY][posX] + 1;

            for (int[] dir : directions) {
                for (int d = 1; d < BOARD_SIZE; d++) {
                    int newY = posY + dir[0] * d, newX = posX + dir[1] * d;
                    if (AmazonsUtility.isSpotValid(board, newY, newX) && distances[newY][newX] > nextDist) {
                        distances[newY][newX] = nextDist;
                        queue.add(new int[]{newY, newX});
                    } else {
                        break;
                    }
                }
            }
        }
    }

    private static double[] calculateKingDistanceMetrics(int[][] board, int playerTurn) {
        int[][] whiteDistances = new int[BOARD_SIZE][BOARD_SIZE];
        int[][] blackDistances = new int[BOARD_SIZE][BOARD_SIZE];
        initializeDistances(whiteDistances);
        initializeDistances(blackDistances);

        propagateKingDistances(board, whiteDistances, WHITE_QUEEN);
        propagateKingDistances(board, blackDistances, BLACK_QUEEN);

        double score = 0.0, controlMetric = 0.0;
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                controlMetric += Math.min(1, Math.max(-1, (blackDistances[i][j] - whiteDistances[i][j]) / 6.0));
                if (whiteDistances[i][j] < blackDistances[i][j]) {
                    score += 1.0;
                } else if (whiteDistances[i][j] > blackDistances[i][j]) {
                    score -= 1.0;
                } else if (whiteDistances[i][j] != Integer.MAX_VALUE) {
                    score += (playerTurn == WHITE_QUEEN ? TURN_ADVANTAGE : -TURN_ADVANTAGE);
                }
            }
        }
        return new double[]{score, controlMetric};
    }

    private static void propagateKingDistances(int[][] board, int[][] distances, int queenType) {
        Queue<int[]> queue = new LinkedList<>();
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                if (board[i][j] == queenType) {
                    queue.add(new int[]{i, j});
                    distances[i][j] = 0;
                }
            }
        }

        int[][] directions = {
            {-1, 0}, {-1, -1}, {0, -1}, {1, -1},
            {1, 0}, {1, 1}, {0, 1}, {-1, 1}
        };

        while (!queue.isEmpty()) {
            int[] pos = queue.poll();
            int posY = pos[0], posX = pos[1];
            int nextDist = distances[posY][posX] + 1;

            for (int[] dir : directions) {
                int newY = posY + dir[0], newX = posX + dir[1];
                if (AmazonsUtility.isSpotValid(board, newY, newX) && distances[newY][newX] > nextDist) {
                    distances[newY][newX] = nextDist;
                    queue.add(new int[]{newY, newX});
                }
            }
        }
    }

    private static double evaluateMobility(int[][] board, int[][] mobilityMap, double w) {
        double whiteScore = 0.0, blackScore = 0.0;

        int[][] directions = {
            {-1, 0}, {-1, -1}, {0, -1}, {1, -1},
            {1, 0}, {1, 1}, {0, 1}, {-1, 1}
        };

        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                if (board[i][j] == WHITE_QUEEN || board[i][j] == BLACK_QUEEN) {
                    double queenEval = 0.0;
                    for (int[] dir : directions) {
                        for (int d = 1; d < BOARD_SIZE; d++) {
                            int newY = i + dir[0] * d, newX = j + dir[1] * d;
                            if (AmazonsUtility.isSpotValid(board, newY, newX)) {
                                queenEval += Math.pow(2, -(d - 1)) * mobilityMap[newY][newX];
                            } else {
                                break;
                            }
                        }
                    }
                    if (board[i][j] == WHITE_QUEEN) {
                        whiteScore += w * Math.pow(1.2, -queenEval) / 45.0;
                    } else {
                        blackScore += w * Math.pow(1.2, -queenEval) / 45.0;
                    }
                }
            }
        }
        return blackScore - whiteScore;
    }
}