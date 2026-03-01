package ubc.cosc322;

public class MonteCarlo {
    // Time allowed for search in millisecond, the root node of the tree, and our exploration parameter
    private long allowedTimeMs;
    public TreeNode root;
    private double explorationCoefficient;
    
    // initializes our MCTS engine with a starting state, search time, and exploration factor
    public MonteCarlo(TreeNode root, long allowedTimeMs, double explorationCoefficient) {
        this.root = root;
        this.allowedTimeMs = allowedTimeMs;
        this.explorationCoefficient = explorationCoefficient;
    }
    
    // Run the Monte Carlo Tree Search and pick the best action from the current root
    public AmazonsAction MCTS() {
        TreeNode.maxDepth = 0;
        long startTime = System.currentTimeMillis();
        int iterations = 0;
        
        // Run our  simulations until the allowed time has passed
        while (System.currentTimeMillis() - startTime < allowedTimeMs) {
            TreeNode leaf = traverse(root);
            double result;
            if (leaf.isTerminal()) {
                result = 1;  // terminal node reached; assign the win value
            } else {
                leaf = leaf.expandAtRandom();
                result = heuristicRollout(leaf);
            }
            iterations++;
            backpropagate(leaf, result);
        }
        System.out.println(iterations + " iterations were run");
        
        //  Pick the action that has the highest win rate among the root's children
        AmazonsAction bestAction = null;
        double bestWinrate = -10000;
        for (TreeNode child : root.children) {
            double winrate = (child.N != 0) ? child.Q / child.N : 0;
            if (winrate > bestWinrate) {
                bestWinrate = winrate;
                bestAction = child.action;
            }
        }
        return bestAction;
    }
    
    // traverse the tree by always selecting the child with the highest UCB until a leaf is reached
    public TreeNode traverse(TreeNode node) {
        if (!node.hasUnexpandedChildren() && node.hasExpandedChildren()) {
            double maxUCB = -1;  //   UCB scores are non-negative
            TreeNode bestChild = null;
            for (TreeNode child : node.children) {
                double currentUCB = child.getUCB(explorationCoefficient);
                if (currentUCB > maxUCB) {
                    maxUCB = currentUCB;
                    bestChild = child;
                }
            }
            return traverse(bestChild);
        }
        return node;
    }
    
    // 		A full rollout using random expansions until a terminal state is reached
    //  0 if the starting player's color loses, 1 otherwise
    public int rollout(TreeNode start) {
        TreeNode currentNode = new TreeNode(start); // copy of the starting node
        while (true) {
            if (currentNode.isTerminal()) {
                return (currentNode.getColor() == start.getColor()) ? 0 : 1;
            }
            currentNode = currentNode.expandAtRandom();
        }
    }
    
    // instead of a full rollout use a heuristic evaluation and a sigmoid to get a rollout value
    public double heuristicRollout(TreeNode node) {
        double heuristicResult = HeuristicEvaluator.getHeuristicEval(node.boardState, node.getColor());
        double result = AmazonsUtility.sigmoid(heuristicResult);
        // Flip the result depending on the player's color.
        return (node.getColor() == 1) ? (1 - result) : result;
    }
    
    // Propagate the simulation result up the tree, updating visit counts and cumulative scores
    public void backpropagate(TreeNode node, double result) {
        node.N++;
        node.Q += result;
        if (node.parent != null) {
            backpropagate(node.parent, 1 - result);
        }
    }
    
    // update the root of the tree based on the action taken If no matching child is found, reconstruct the state
    public void rootFromAction(AmazonsAction a) {
        this.root.expand();
        boolean found = false;
        for (TreeNode child : root.children) {
            if (child.action.isEqual(a)) {
                root = child;
                root.parent = null;
                found = true;
                break;
            }
        }
        if (!found) {
            // In the case of an illegal move adjust the state manually
            int newColor = (root.color == 2) ? 1 : 2;
            int[][][] postCheatState = AmazonsAction.applyAction(a, root.boardState);
            root = new TreeNode(postCheatState, newColor);
        }
    }
}