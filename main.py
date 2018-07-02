# This is a very simple implementation of the UCT Monte Carlo Tree Search algorithm in Python 2.7.
# The function UCT(rootstate, itermax, verbose = False) is towards the bottom of the code.
# It aims to have the clearest and simplest possible code, and for the sake of clarity, the code
# is orders of magnitude less efficient than it could be made, particularly by using a
# state.GetRandomMove() or state.DoRandomRollout() function.
#
# Example GameState classes for Nim, OXO and Othello are included to give some idea of how you
# can write your own GameState use UCT in your 2-player game. Change the game to be played in
# the UCTPlayGame() function at the bottom of the code.
#
# Written by Peter Cowling, Ed Powley, Daniel Whitehouse (University of York, UK) September 2012.
#
# Licence is granted to freely use and distribute for any sensible/legal purpose so long as this comment
# remains in any distributed code.
#
# For more information about Monte Carlo Tree Search check out our web site at www.mcts.ai

from math import *
import random
import copy
import math
import time
from multiprocessing import Process, Queue, Lock

def get_grid_from_cords(x, y):
    return int(math.floor(y/3)) * 3 + int(math.floor(x/3))

def get_offset_for_grid(number):
    return [
        number%3 * 3,
        int(math.floor(number/3)) * 3
    ]

class OXOState:
    """ A state of the game, i.e. the game board.
        Squares in the board are in this arrangement
        012
        345
        678
        where 0 = empty, 1 = player 1 (X), 2 = player 2 (O)
    """

    def __init__(self):
        self.playerJustMoved = 0  # At the root pretend the player just moved is p2 - p1 has the first move
        self.lastMove = [-1,-1]
        self.board = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0]
            ]# 0 = empty, 1 = player 1, 2 = player 2

    def Clone(self):
        """ Create a deep clone of this game state.
        """
        st = OXOState()
        st.playerJustMoved = self.playerJustMoved
        st.board = copy.deepcopy(self.board)
        st.lastMove = copy.deepcopy(self.lastMove)
        return st

    def DoMove(self, move):
        """ Update a state by carrying out the given move.
            Must update playerToMove.
        """
        coords = [move % 9, math.floor(move / 9)]
        assert move >= 0 and move <= 80 and move == int(move) and self.board[coords[1]][coords[0]] == 0
        self.playerJustMoved = 1 if (self.playerJustMoved == 2 or self.playerJustMoved == 0) else 2
        self.board[coords[1]][coords[0]] = self.playerJustMoved
        self.lastMove = coords

    def GetMoves(self):
        """ Get all possible moves from this state.
        """
        ## Using first player, because we are only interested in a draw anyway
        large_result = self.CheckForLargeResult(1)
        if large_result != -1:
            return []

        if self.lastMove[0] == self.lastMove[1] == -1:
            return [i for i in range(81) if self.board[math.floor(i / 9)][i % 9] == 0]

        gridNumber = self.lastMove[0]%3 + self.lastMove[1]%3 * 3
        offset = get_offset_for_grid(gridNumber)
        gridWinner = self.GetGridWinner(gridNumber)
        moves = []
        if gridWinner == 0:
            moves = [((math.floor(i / 3) + offset[1]) * 9 + i % 3 + offset[0]) for i in range(9) if self.board[math.floor(i / 3) + offset[1]][i % 3 + offset[0]] == 0]

        if len(moves) == 0:
            for gN in range(9):
                if self.GetGridWinner(gN) == 0:
                    offset = get_offset_for_grid(gN)
                    moves.extend([((math.floor(i / 3) + offset[1]) * 9 + i % 3 + offset[0]) for i in range(9) if self.board[math.floor(i / 3) + offset[1]][i % 3 + offset[0]] == 0])
            # moves = [i for i in range(81) if self.board[math.floor(i / 9)][i % 9] == 0]
        return moves

    def SimplifyBoard(self):
        return [self.board[math.floor(i / 9)][i % 9] for i in range(81)]

    def GetGridWinner(self, gridNumber):
        offset = get_offset_for_grid(gridNumber)
        lines = [(0, 1, 2), (9, 10, 11), (18, 19, 20), (0, 9, 18), (1, 10, 19), (2, 11, 20), (0, 10, 20), (2, 10, 18)]
        lines = map(lambda x: map(lambda y: y + offset[0] + offset[1]*9, x), lines)
        simpleBoard = self.SimplifyBoard()
        for (x, y, z) in lines:
            if simpleBoard[x] == simpleBoard[y] == simpleBoard[z]:
                if simpleBoard[x] > 0:
                    return simpleBoard[x]
        return 0

    def GetLargeGrid(self):
        return [self.GetGridWinner(0), self.GetGridWinner(1), self.GetGridWinner(2),
                self.GetGridWinner(3), self.GetGridWinner(4), self.GetGridWinner(5),
                self.GetGridWinner(6), self.GetGridWinner(7), self.GetGridWinner(8)]

    def CheckForLargeResult(self, playerjm):
        grid = self.GetLargeGrid()
        for (x, y, z) in [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]:
            if grid[x] == grid[y] == grid[z] and grid[x] > 0:
                if grid[x] == playerjm:
                    return 1.0
                else:
                    return 0
        return -1

    def GetResult(self, playerjm):
        """ Get the game result from the viewpoint of playerjm.
        """
        large_result = self.CheckForLargeResult(playerjm)
        if large_result != -1:
            return large_result

        grid = self.GetLargeGrid()
        if len(self.GetMoves()) == 0:
            s = 0
            for i in range(9):
                s += 1 if grid[i] == playerjm else -1 if grid[i] == (3 - playerjm) else 0
            if s > 0:
                return 1.0
            elif s == 0:
                return 0.5
            else:
                return 0
        else:
            return -1
        # assert False  # Should not be possible to get here

    def __repr__(self):
        s = ""
        for i in range(81):
            s += ".XO"[self.board[math.floor(i/9)][i%9]]
            if i % 3 == 2: s += " | "
            if i % 9 == 8: s += "\n"
            if i % 27 == 26: s += "-----------------\n"
        return s

class Node:
    """ A node in the game tree. Note wins is always from the viewpoint of playerJustMoved.
        Crashes if state not specified.
    """

    def __init__(self, move=None, parent=None, state=None):
        self.move = move  # the move that got us to this node - "None" for the root node
        self.parentNode = parent  # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        self.untriedMoves = state.GetMoves()  # future child nodes
        self.playerJustMoved = state.playerJustMoved  # the only part of the state that the Node needs later

    def UCTSelectChild(self):
        """ Use the UCB1 formula to select a child node. Often a constant UCTK is applied so we have
            lambda c: c.wins/c.visits + UCTK * sqrt(2*log(self.visits)/c.visits to vary the amount of
            exploration versus exploitation.
        """
        s = sorted(self.childNodes, key=lambda c: c.wins / c.visits + math.sqrt(2 * math.log(self.visits) / c.visits))[-1]
        return s

    def AddChild(self, m, s):
        """ Remove m from untriedMoves and add a new child node for this move.
            Return the added child node
        """
        n = Node(move=m, parent=self, state=s)
        self.untriedMoves.remove(m)
        self.childNodes.append(n)
        return n

    def Update(self, result):
        """ Update this node - one additional visit and result additional wins. result must be from the viewpoint of playerJustmoved.
        """
        self.visits += 1
        self.wins += result

    def __repr__(self):
        return "[M:" + str(self.move) + " W/V:" + str(self.wins) + "/" + str(self.visits) + " U:" + str(
            self.untriedMoves) + "]"

    def TreeToString(self, indent):
        s = self.IndentString(indent) + str(self)
        for c in self.childNodes:
            s += c.TreeToString(indent + 1)
        return s

    def IndentString(self, indent):
        s = "\n"
        for i in range(1, indent + 1):
            s += "| "
        return s

    def ChildrenToString(self):
        s = ""
        for c in self.childNodes:
            s += str(c) + "\n"
        return s


def UCT(rootstate, itermax, verbose=False):
    """ Conduct a UCT search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.
        Assumes 2 alternating players (player 1 starts), with game results in the range [0.0, 1.0]."""

    rootnode = Node(state=rootstate)

    start_time = time.time()
    loops = 0;
    while True:
        loop_start_time = time.time()
        loops += 1
    # for i in range(itermax):
        node = rootnode
        state = rootstate.Clone()

        # Select
        while node.untriedMoves == [] and node.childNodes != []:  # node is fully expanded and non-terminal
            node = node.UCTSelectChild()
            state.DoMove(node.move)

        # Expand
        if node.untriedMoves != []:  # if we can expand (i.e. state/node is non-terminal)
            m = random.choice(node.untriedMoves)
            state.DoMove(m)
            node = node.AddChild(m, state)  # add child and descend tree

        # Rollout - this can often be made orders of magnitude quicker using a state.GetRandomMove() function
        while state.GetMoves() != []:  # while state is non-terminal
            state.DoMove(random.choice(state.GetMoves()))

        # Backpropagate
        while node != None:  # backpropagate from the expanded node and work back to the root node
            node.Update(state.GetResult(
                node.playerJustMoved))  # state is terminal. Update node with result from POV of node.playerJustMoved
            node = node.parentNode

        cur_time = time.time()
        loop_time = cur_time - loop_start_time
        print("loop time:", loop_time)
        if (cur_time + loop_time) > (start_time + 0.001 * itermax):
            break

    # Output some information about the tree - can be omitted
    if (verbose):
        # print(rootnode.TreeToString(0))
        pass
    else:
        # print(rootnode.ChildrenToString())
        pass

    if len(rootnode.childNodes) == 0:
        print("hmm", loops)
        # print(rootstate)
        print(rootnode.TreeToString(0))

    print("loops", loops)
    return sorted(sorted(rootnode.childNodes, key=lambda c: c.wins), key=lambda c: c.visits)[-1].move  # return the move that was most visited


def UCTPlayGame(max_iterations):
    """ Play a sample game between two UCT players where each player gets a different number
        of UCT iterations (= simulations = tree nodes).
    """
    # state = OthelloState(4) # uncomment to play Othello on a square board of the given size
    state = OXOState() # uncomment to play OXO
    # state = NimState(15)  # uncomment to play Nim with the given number of starting chips
    while (state.GetMoves() != []):
        # print(str(state))
        if state.playerJustMoved == 2 or state.playerJustMoved == 0:
            m = UCT(rootstate=state, itermax=max_iterations, verbose=False)  # player 1
        else:
            # m = UCT(rootstate=state, itermax=max_iterations, verbose=False) # player 2
            m = random.choice(state.GetMoves())
        # print("Best Move: " + str(m) + "\n")
        state.DoMove(m)

    # print(str(state))

    if state.GetResult(state.playerJustMoved) == 1.0:
        print("Player " + str(state.playerJustMoved) + " wins!")
        return state.playerJustMoved
    elif state.GetResult(state.playerJustMoved) == 0.0:
        print("Player " + str(3 - state.playerJustMoved) + " wins!")
        return 3 - state.playerJustMoved
    else:
        print("Nobody wins!")
        return 0

game_instance = None

class UCTPlayer:
    def __init__(self, max_iterations):
        self.state = OXOState()
        self.playerNum = 1
        self.maxIterations = max_iterations
        pass

    def get_move(self, opponentAction, validActions):
        if opponentAction[0] == opponentAction[1] == -1:
            self.playerNum = 2
        else:
            self.state.DoMove(opponentAction[0] + opponentAction[1] * 9)

        # moves = self.state.GetMoves()
        # validate that moves and validActions are the same
        # error = False
        # if len(moves) != len(validActions):
        #     error = True
        #
        # for i in moves:
        #     cords = [i % 9, math.floor(i / 9)]
        #     if cords not in validActions:
        #         error = True
        #
        # if error:
        #     print("Something is wrong")
        #     print(self.state)
        #     global game_instance
        #     game_instance.printGrid()
        #     print([ [i % 9, math.floor(i / 9)] for i in moves ])
        #     print(validActions)
        move = None
        if len(validActions) > 0:
            m = UCT(rootstate=self.state, itermax=self.maxIterations, verbose=True)
            # print(m)
            self.state.DoMove(m)
            # cur_result = self.state.GetResult(3-self.playerNum)
            # if cur_result == 1.0:
            #     print("I won", self.playerNum)
            # elif cur_result == 0:
            #     print("I lost", self.playerNum)
            move = [m % 9, math.floor(m / 9)]
        else:
            pass

        return move

    def getResult(self):
        return self.state.GetResult(3 - self.playerNum)


import tictactoe
import ticplayer


def play_game():
    player1 = UCTPlayer(101)
    player2 = ticplayer.BasicPlayer()
    large = True
    game_instance = tictactoe.Game(large, player1, player2)
    result = game_instance.play()
    if result != 1 if player1.getResult() == 1.0 else 2:
        pass
    return result

def worker(q, lock):
    """thread worker function"""
    # print("started")
    result = play_game()
    # print("finished")
    lock.acquire()
    win_rate = q.get()
    # print("got q", win_rate)
    if result == 1:
        win_rate += 1
    elif result == 0:
        win_rate += 0.5

    q.put(win_rate)
    # print("put q", win_rate)
    lock.release()
    return

def get_win_rate(number):
    lock = Lock()
    q = Queue()
    win_rate = 0
    q.put(win_rate)
    ts = []
    for i in range(number):
        t = Process(target=worker, args=(q, lock,))
        t.start()
        ts.append(t)

    for t in ts:
        t.join()

    win_rate = q.get()

    return win_rate * (100/number)

def evaluate_solution():
    games = 1000;
    divider = 0
    win_rate_single = 0
    jobs = 1
    while games > 0:
        temp_games = min(jobs, games)
        games -= temp_games
        divider += 1
        win_rate_single += get_win_rate(temp_games)
        print(win_rate_single / divider)

import matplotlib.pyplot as plt

def graph_things():
    games = 1000
    maximum_iters = 101
    iters_steps = 5

    plt.axis([0, maximum_iters, 0, games])

    for max_iters in range(1, maximum_iters + 1, iters_steps):
        s = 0
        for i in range(games):
            r = UCTPlayGame(max_iters)
            s += 1 if r == 1 else 0.5 if r == 0 else 0
            plt.pause(0.05)
            print(i + 1, s)

        plt.scatter(max_iters, s)
        plt.pause(0.05)
        print(s)

    plt.show()


if __name__ == "__main__":
    """ Play a single game to the end using UCT for both players. 
    """
    evaluate_solution()
    # while True:
    # print(play_game())
    # UCTPlayGame(100)
    # graph_things()




