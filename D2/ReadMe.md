Once the AI's search reaches the time limit, it will be forced to return the current best move. Because the ai iterate the board in a fixed way, to avoid returning the same move all the time, the list the moves will be shuffled randomly every time so that the ai will perform different moves.  

Th move returning time is set to 0.01, when it is detected that the time left is less than o.o1 the algorithm will start to return the current best move. If the returning time exceeds 0.01, the current ai will lose the game automatically.  

The heuristic designed:  
For both heuristics, the weight of AI's existence is 9999 to make sure the program will be able to detect win/lose cases.
To switch to a different heuristic, please change the code in the main menu. The user is not allowed to enter the heuristic from the terminal. The heuristic choice is an integer (0, 1, 2) representing the heuristic, default is 0.

Heuristic 1:  
Heuristic 1 is designed based on the position of each unit. It evaluates the distance between units and the ai, and assign different weight to the distance. For example, for the attacker, the distance between the virus and the defender's AI will be assigned more weight than the distance between the firewall and the defender's AI. The heuristic has the following assumptions:  
each player wants to make units that are good at attacking as close as possible to the other player's AI and place the units that are good at defending as close as possible to their own AI.  
Each player will have two different evaluations and these two evaluations will be combined together to calculate the final mark. One of them is for defending their own AI and the other is for attacking the enemy's AI. The combinations will be then used to calculate the evaluation score of the state for the current user.
Since the defender and the attacker have different types of units, the evaluation will be first performed on each player's unit status, and then calculate the difference between the two scores to check the advantage of the current state. For each player, their combination mark will be the sum of their attacking mark and the defending mark. To make the scare the greater the better, the final evaluation mark of one player will be: the combination mark of the other player minus the current player's combination mark, since players want the distance to be as small as possible.

Heuristic 2:  
Heuristic 2 is designed based on the health condition of the units. It is assumed that all players want to have full health for their own units and hurt the enemy's units as much as possible. Different types of units are assigned different health weights, considering that some units are more valuable than others. For example, viruses are more valuable than programs for attacker. The final score will be the health mark of the current user minus the health mark of the other user. The greater the better.

The displayed statics for one AI move:

Average recursive depth: the average depth of each search

Evals per depth:  how many evaluation is performed in one search. The program will calculate how many nodes are actually evaluated per depth, which means that the number of the received returned value of one depth will be the evaluation number of its next depth. The root is considered to be at depth 1, which means the evaluation time of the root is one.

Cumulative evals: The sum of the evaluation per depth  
Cumulative % evals by depth: The percentage notation of cumulative evals  
Average branching factor: the average children number of one node.  

Eval perf.: how long does it take to perform one evaluation.  
Elapsed time: how long does it take for AI to find the best move.
