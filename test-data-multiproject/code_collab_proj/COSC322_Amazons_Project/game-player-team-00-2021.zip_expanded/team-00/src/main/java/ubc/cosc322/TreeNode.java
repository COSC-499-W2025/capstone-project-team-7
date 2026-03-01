package ubc.cosc322;

import java.util.ArrayList;

public class TreeNode {
    public static int maxDepth = 0;  // tracks maximum depth encountered in the tree
    int depth;                // depth of this node in the tree
    int color;                // current player's color at this node
    double Q;                 // the Cumulative reward
    int N;                    //  Visit count
    int[][][] boardState;     // gameboard state (layer 0: board; layer 1: mobility map)
    AmazonsAction action;     // 	Action taken to reach this node (null for the root)
    TreeNode parent;          // Parent node (null for the root)
    ArrayList<TreeNode> children;         //   Expanded child nodes.
    ArrayList<AmazonsAction> possibleActions; //list of the  moves not yet expanded
    boolean expanded;         // whether this node has been fully expanded
    boolean actionsGenerated; //whether the list of Possible Actions has been Generated
    
    //	Child Node: Create a new node by applying an action to a parent's state
    public TreeNode(int[][][] boardState, TreeNode parent, AmazonsAction action) {
        this.boardState = boardState;
        this.parent = parent;
        this.action = action;
        // Flip the color: if parent's color is 2, child becomes 1; otherwise 2.
        this.color = (parent.color == 2) ? 1 : 2;
        this.children = new ArrayList<>();
        this.expanded = false;
        this.actionsGenerated = false;
        this.depth = parent.depth + 1;
        this.N = 0;
        this.Q = 0;
        if (this.depth > maxDepth) {
            maxDepth = this.depth;
            System.out.println("Depth: " + maxDepth);
        }
    }
    
    //	Root Node: Initialize the tree with an initial board state and starting color
    public TreeNode(int[][][] boardState, int color){
        this.boardState = boardState;
        this.color = color;
        this.parent = null;
        this.action = null;
        this.children = new ArrayList<>();
        this.expanded = false;
        this.actionsGenerated = false;
        this.depth = 0;
        this.N = 0;
        this.Q = 0;
    }
    
    // 	Copy Constructor: For rollouts, create a a shallow copy of actions and state
    public TreeNode(TreeNode copyNode) {
        this.boardState = copyNode.boardState;
        this.possibleActions = copyNode.possibleActions;
        this.color = copyNode.color;
        this.expanded = false;
        this.actionsGenerated = copyNode.actionsGenerated;
        this.children = new ArrayList<>();
    }
    
    // check if this node has no further moves
    public boolean isTerminal() {
        if (!this.actionsGenerated) {
            generateActions();
        }
        return this.possibleActions.isEmpty() && this.children.isEmpty();
    }
    
    // true if still moves to expand.
    public boolean hasUnexpandedChildren() {
        if (!this.actionsGenerated) {
            generateActions();
        }
        return !this.possibleActions.isEmpty();
    }
    
    // true if this node already has at least one child
    public boolean hasExpandedChildren() {
        return !this.children.isEmpty();
    }
    
    //return the current player's color at this node
    public int getColor() {
        return this.color;
    }
    
    // Get the of count the moves not yet expanded
    public int getNumPossibleActions(){
        if (!this.actionsGenerated) {
            generateActions();
        }
        return this.possibleActions.size();
    }
    
    //  generate the list of all possible moves from this board state
    private void generateActions(){
        this.possibleActions = AmazonsActionFactory.getActions(this.boardState, this.color);
        this.actionsGenerated = true;
    }
    
    // Create a new child node using the provided action
    public TreeNode generateChild(AmazonsAction action) {
        TreeNode child = new TreeNode(AmazonsAction.applyAction(action, this.boardState), this, action);
        this.children.add(child);
        return child;
    }
    
    // expand this node by generating children for every possible move
    public void expand() {
        if (!this.actionsGenerated){
            generateActions();
        }
        for (AmazonsAction a : this.possibleActions) {
            this.children.add(new TreeNode(AmazonsAction.applyAction(a, this.boardState), this, a));
        }
        this.possibleActions.clear();
        this.expanded = true;
    }
    
    // randomly pick an action to expand, useful for rollout paths
    public TreeNode expandAtRandom(){
        if (!this.actionsGenerated) {
            generateActions();
        }
        int index = (int) (Math.random() * getNumPossibleActions());
        AmazonsAction action = this.possibleActions.get(index);
        this.possibleActions.remove(index);
        if (this.possibleActions.isEmpty()) {
            this.expanded = true;}
        return generateChild(action);
    }
    
    // compute the UCB value to balance exploration and exploitation,
    // unvisited nodes return a high constant to force exploration.
    public double getUCB(double explorationParam) {
        if (N == 0) return 10000.0;
        return (Q / N) + explorationParam * Math.sqrt(Math.log(parent.N) / N);
    }

    public void printBoard() {
        AmazonsUtility.printBoard(this.boardState[0]);
    }
}