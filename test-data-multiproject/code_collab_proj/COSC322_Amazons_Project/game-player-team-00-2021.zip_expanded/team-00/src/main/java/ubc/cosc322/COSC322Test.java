package ubc.cosc322;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import sfs2x.client.entities.Room;
import ygraph.ai.smartfox.games.BaseGameGUI;
import ygraph.ai.smartfox.games.GameClient;
import ygraph.ai.smartfox.games.GameMessage;
import ygraph.ai.smartfox.games.GamePlayer;
import ygraph.ai.smartfox.games.amazons.AmazonsGameMessage;
import ygraph.ai.smartfox.games.amazons.HumanPlayer;

public class COSC322Test extends GamePlayer {

    //our connection objects: the game client and GUI
    private GameClient client;
    private BaseGameGUI gui;

    // username and a placeholder password
    private String username;
    private String password;

    // Game engine variables: Monte Carlo search instance and identifiers for pieces
    private MonteCarlo monteCarlo;
    private final int WHITE_QUEEN = 1;
    private final int BLACK_QUEEN = 2;
    private final int ARROW = 3; // Just a distinct value from the queens
    private int myQueen = -1;
    private int opponentQueen = -1;

    // provide a username as an argument
    public static void main(String[] args) {
        String uname = "cosc322";
        if (args.length > 0) {
            uname = args[0];
        }
        COSC322Test gamePlayer = new COSC322Test(uname, "cosc322");

        // decide whether to run headless or start the GUI event loop
        if (gamePlayer.getGameGUI() == null) {
            gamePlayer.Go();
        } else {
            BaseGameGUI.sys_setup();
            java.awt.EventQueue.invokeLater(new Runnable() {
                public void run() {
                    gamePlayer.Go();
                }
            });
        }
    }

    //  sets up user credentials and instantiates the GUI
    public COSC322Test(String username, String password) {
        this.username = username;
        this.password = password;
        this.gui = new BaseGameGUI(this);
    }

    @Override
    public void connect() {
        client = new GameClient(username, password, this);
    }

    @Override
    public String userName() {
        return username;
    }

    @Override
    public GameClient getGameClient() {
        return client;
    }

    @Override
    public BaseGameGUI getGameGUI() {
        return gui;
    }

    //Called once login is successful. It updates the GUI with room info and auto-joins the first room
    @Override
    public void onLogin() {
        username = client.getUserName();
        List<Room> roomList = client.getRoomList();

        if (gui != null) {
            gui.setRoomInformation(roomList);
        }

        if (!roomList.isEmpty()) {
            String roomToJoin = roomList.get(0).getName();
            System.out.println("Joining room: " + roomToJoin);
            client.joinRoom(roomToJoin);
        } else {
            System.out.println("Couldn't find any room to join!");
        }
    }

    // New method: allows the user to manually join a different room from the GUI
    public void joinRoom(String roomName) {
        System.out.println("Joining room: " + roomName);
        client.joinRoom(roomName);
    }

    // Responds to game messages coming from the server
    @SuppressWarnings("unchecked")
    @Override
    public boolean handleGameMessage(String messageType, Map<String, Object> msgDetails) {
        switch (messageType) {
            case GameMessage.GAME_STATE_BOARD:
                ArrayList<Integer> boardState = (ArrayList<Integer>) msgDetails.get(AmazonsGameMessage.GAME_STATE);
                gui.setGameState(boardState);
                monteCarlo = null;
                System.out.println("Board state received.");
                break;

            case GameMessage.GAME_ACTION_MOVE:
                ArrayList<Integer> currentQueenPos = (ArrayList<Integer>) msgDetails.get(AmazonsGameMessage.QUEEN_POS_CURR);
                ArrayList<Integer> nextQueenPos = (ArrayList<Integer>) msgDetails.get(AmazonsGameMessage.QUEEN_POS_NEXT);
                ArrayList<Integer> arrowPos = (ArrayList<Integer>) msgDetails.get(AmazonsGameMessage.ARROW_POS);
                processOpponentMove(currentQueenPos, nextQueenPos, arrowPos);
                if (monteCarlo != null) {
                    executeMove();
                }
                break;

            case GameMessage.GAME_ACTION_START:
                String whitePlayer = (String) msgDetails.get(AmazonsGameMessage.PLAYER_WHITE);
                String blackPlayer = (String) msgDetails.get(AmazonsGameMessage.PLAYER_BLACK);
                SetMyQueen(whitePlayer, blackPlayer);
                InitalizeBoard();
                if (myQueen == BLACK_QUEEN) {
                    executeMove();
                }
                break;
            case "cosc322.game-state.userlost":
                // Handle the user lost message
                System.out.println("Received game-state.userlost. Game over.");
                break;

            default:
                System.out.println("Unhandled message type: " + messageType);
                assert (false);
                break;
        }
        return true;
    }

    public void SetMyQueen(String whitePlayer, String blackPlayer) {
        assert (!whitePlayer.equals(blackPlayer));
        if (username.equals(whitePlayer)) {
            myQueen = WHITE_QUEEN;
            opponentQueen = BLACK_QUEEN;
        } else if (username.equals(blackPlayer)) {
            myQueen = BLACK_QUEEN;
            opponentQueen = WHITE_QUEEN;
        } else {
            System.out.println("Fatal error, invalid queen value received " + myQueen + ", please restart");
            assert (false);
        }

        System.out.println("SetMyQueen " + myQueen);
    }

    public void executeMove() {
        // assert that monte carlo is tracking turns properly as we can only make moves on our turn
        assert (monteCarlo.root.getColor() == myQueen);

        AmazonsAction action = monteCarlo.MCTS();
        if (action != null) {
            ArrayList<Integer> aiQueenPosCurr = new ArrayList<Integer>();
            aiQueenPosCurr.add(action.queenSrcY + 1);
            aiQueenPosCurr.add(action.queenSrcX + 1);

            ArrayList<Integer> aiQueenPosNext = new ArrayList<Integer>();
            aiQueenPosNext.add(action.queenDestY + 1);
            aiQueenPosNext.add(action.queenDestX + 1);

            ArrayList<Integer> aiArrowPos = new ArrayList<Integer>();
            aiArrowPos.add(action.arrowDestY + 1);
            aiArrowPos.add(action.arrowDestX + 1);

            gui.updateGameState(aiQueenPosCurr, aiQueenPosNext, aiArrowPos);
            client.sendMoveMessage(aiQueenPosCurr, aiQueenPosNext, aiArrowPos);
            monteCarlo.rootFromAction(action);
        } else { // action is only null when you lose, as you have no actions available
            System.out.println("You lose.");
			System.exit(0); // if you lose then disconnect from the game
            // TODO: is there a server message you send once the game is over?
        }
    }

    public void processOpponentMove(ArrayList<Integer> currQueenPos, ArrayList<Integer> nextQueenPos,
                                    ArrayList<Integer> arrowPos) {
        AmazonsAction action = new AmazonsAction(
            currQueenPos.get(1) - 1,
            currQueenPos.get(0) - 1,
            nextQueenPos.get(1) - 1,
            nextQueenPos.get(0) - 1,
            arrowPos.get(1) - 1,
            arrowPos.get(0) - 1
        );
        gui.updateGameState(currQueenPos, nextQueenPos, arrowPos);
        if (monteCarlo != null) {
            monteCarlo.rootFromAction(action);

			//check to see if opponenet has no moves on their turn:
			if(opponentHasNoMoves()){
				System.out.println("You Win!");
				System.exit(0); // if so you won, and disconnect from the game
			}
        }
    }

    public void InitalizeBoard() {
        System.out.println("Initializing board");

        int[][][] state = new int[2][10][10];

        // hard coded but ideally set using stateArr
        state[0][0][3] = WHITE_QUEEN;
        state[0][0][6] = WHITE_QUEEN;

        state[0][3][0] = WHITE_QUEEN;
        state[0][3][9] = WHITE_QUEEN;

        state[0][6][0] = BLACK_QUEEN;
        state[0][6][9] = BLACK_QUEEN;

        state[0][9][3] = BLACK_QUEEN;
        state[0][9][6] = BLACK_QUEEN;

        state[1] = AmazonsUtility.getMobilityMap(state[0]);
        AmazonsUtility.printBoard(state[0]);

        monteCarlo = new MonteCarlo(new TreeNode(state, BLACK_QUEEN), 5000, 1.4);
    }

	private boolean opponentHasNoMoves() {
		// The opponent's color is the one not equal to myQueen
		int opponentColor = (myQueen == WHITE_QUEEN) ? BLACK_QUEEN : WHITE_QUEEN;
		// Generate all possible actions for the opponent using the current board state.
		ArrayList<AmazonsAction> opponentActions = AmazonsActionFactory.getActions(monteCarlo.root.boardState, opponentColor);
		return opponentActions.isEmpty();
	}
	
}