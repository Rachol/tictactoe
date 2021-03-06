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


class BasicOXOState:
    """ A state of the game, i.e. the game board.
        Squares in the board are in this arrangement
        012
        345
        678
        where 0 = empty, 1 = player 1 (X), 2 = player 2 (O)
    """

    def __init__(self, board):
        self.playerJustMoved = 2  # At the root pretend the player just moved is p2 - p1 has the first move
        self.board = copy.deepcopy(board)  # 0 = empty, 1 = player 1, 2 = player 2

    def Clone(self):
        """ Create a deep clone of this game state.
        """
        st = BasicOXOState(self.board)
        st.playerJustMoved = self.playerJustMoved
        return st

    def DoMove(self, move):
        """ Update a state by carrying out the given move.
            Must update playerToMove.
        """
        assert move >= 0 and move <= 8 and move == int(move) and self.board[move] == 0
        self.playerJustMoved = 3 - self.playerJustMoved
        self.board[move] = self.playerJustMoved

    def GetMoves(self):
        """ Get all possible moves from this state.
        """
        return [i for i in range(9) if self.board[i] == 0]

    def GetResult(self, playerjm):
        """ Get the game result from the viewpoint of playerjm.
        """
        for (x, y, z) in [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]:
            if self.board[x] == self.board[y] == self.board[z]:
                if self.board[x] == playerjm:
                    return 1.0
                else:
                    return 0.0
        if self.GetMoves() == []: return 0.5  # draw
        assert False  # Should not be possible to get here

    def __repr__(self):
        s = ""
        for i in range(9):
            s += ".XO"[self.board[i]]
            if i % 3 == 2: s += "\n"
        return s


class GameBoard:
    def __init__(self):
        self.p1 = Board(0)
        self.p2 = Board(0)
        self.lastMove = -1

    def GetMoves(self):
        ## First check if any of the players won
        if self.p1.CheckWin():
            # self.p1.PrintLargeBoard(self.p1.GetData())
            # self.p1.PrintSmallBoard(self.p1.GetResultBoard())
            return []
        if self.p2.CheckWin():
            # self.p2.PrintLargeBoard(self.p2.GetData())
            # self.p2.PrintSmallBoard(self.p2.GetResultBoard())
            return []

        c = Board(self.p1.GetData() | self.p2.GetData())
        if self.lastMove == -1:
            return [i for i in range(81)]

        gn = self.p1.GetNextMoveBoardNumber(self.lastMove)
        ##Check if any moves available on that board
        small_board = c.ExtractSmallBoard(gn)
        if (0b111111111 - small_board) == 0 or \
                self.p1.CheckSmallWin(self.p1.ExtractSmallBoard(gn)) or \
                self.p2.CheckSmallWin(self.p2.ExtractSmallBoard(gn)):
            moves = []
            for g in range(9):
                if not (self.p1.CheckSmallWin(self.p1.ExtractSmallBoard(g)) or
                        self.p2.CheckSmallWin(self.p2.ExtractSmallBoard(g))):
                    small_board = c.ExtractSmallBoard(g)
                    moves.extend(
                        [self.p1.TranslateMoveFromSmallBoard(i, g) for i in range(9) if ((small_board >> i) & 1) == 0])
            return moves
        else:
            return [self.p1.TranslateMoveFromSmallBoard(i, gn) for i in range(9) if ((small_board >> i) & 1) == 0]

    def GetData(self):
        return self.p1.GetData() | self.p2.GetData()

    def Move(self, move, player):
        if player == 1:
            self.p1.Move(move)
            pass
        elif player == 2:
            self.p2.Move(move)
            pass
        self.lastMove = move

    def GetResult(self, player):
        if self.p1.CheckWin():
            return 1.0 if player == 1 else -1.0
        if self.p2.CheckWin():
            return 1.0 if player == 2 else -1.0

        player1_result_board = self.p1.GetResultBoard()
        player2_result_board = self.p2.GetResultBoard()

        score = 0
        for i in range(9):
            score += (player1_result_board & (1 << i))
            score -= (player2_result_board & (1 << i))

        return 0.5 if score == 0 else 1.0 if (score > 0 and player == 1 or score < 0 and player == 2) else -1.0

    def __repr__(self):
        s = ""
        for i in range(81):
            p1 = 1 if (self.p1.GetData() & (1 << i)) != 0 else 0
            p2 = 2 if (self.p2.GetData() & (1 << i)) != 0 else 0
            s += ".XO?"[p1 + p2]
            if i % 3 == 2: s += " | "
            if i % 9 == 8: s += "\n"
            if i % 27 == 26: s += "-----------------\n"

        player1_result_board = self.p1.GetResultBoard()
        player2_result_board = self.p2.GetResultBoard()
        for i in range(9):
            p1 = 1 if (player1_result_board >> i) & 1 else 0
            p2 = 2 if (player2_result_board >> i) & 1 else 0
            s += ".XO?"[p1 + p2]
            if i % 3 == 2: s += "\n"

        return s


class Board:
    def __init__(self, d):
        self.d = d
        self.mNSB = []
        for i in range(81):
            self.mNSB.append(math.floor((i % 27) / 9) * 3 + i % 3)

        self.sTLM = []
        for i in range(9):
            offset = [i % 3 * 3, int(math.floor(i / 3)) * 3]
            self.sTLM.append([((math.floor(ii / 3) + offset[1]) * 9 + ii % 3 + offset[0]) for ii in range(9)])

    def Move(self, move):
        self.d |= (1 << move)

    def GetData(self):
        return self.d

    def GetNextMoveBoardNumber(self, move):
        return self.mNSB[move]

    def TranslateMoveFromSmallBoard(self, move, boardNumber):
        return self.sTLM[boardNumber][move]

    # This does not take into account who has more little wins
    def CheckWin(self):
        return self.CheckSmallWin(self.GetResultBoard())

    def GetResultBoard(self):
        result_board = 0
        for i in range(9):
            result_board |= ((self.CheckSmallWin(self.ExtractSmallBoard(i)) << i) & (1 << i))
        return result_board

    def PrintSmallBoard(self, data):
        s = ""
        for i in range(9):
            p1 = 1 if (data & (1 << i)) != 0 else 0
            s += ".Q"[p1]
            if i % 3 == 2: s += "\n"
        print(s)

    def PrintLargeBoard(self, data):
        s = ""
        for i in range(81):
            p1 = 1 if (data & (1 << i)) != 0 else 0
            s += ".Q"[p1]
            if i % 3 == 2: s += " | "
            if i % 9 == 8: s += "\n"
            if i % 27 == 26: s += "-----------------\n"
        print(s)

    def CheckSmallWin(self, d):
        # 9 options
        return (d & 0b000000111) == 0b000000111 or \
               (d & 0b000111000) == 0b000111000 or \
               (d & 0b111000000) == 0b111000000 or \
               (d & 0b001001001) == 0b001001001 or \
               (d & 0b010010010) == 0b010010010 or \
               (d & 0b100100100) == 0b100100100 or \
               (d & 0b100010001) == 0b100010001 or \
               (d & 0b001010100) == 0b001010100

    def ExtractSmallBoard(self, number):
        board = 0
        d = self.d
        if number == 0:
            board = ((d >> 0 & 0b111) << 0) | ((d >> 9 & 0b111) << 3) | ((d >> 18 & 0b111) << 6)
            pass
        elif number == 1:
            board = ((d >> 3 & 0b111) << 0) | ((d >> 12 & 0b111) << 3) | ((d >> 21 & 0b111) << 6)
            pass
        elif number == 2:
            board = ((d >> 6 & 0b111) << 0) | ((d >> 15 & 0b111) << 3) | ((d >> 24 & 0b111) << 6)
            pass
        elif number == 3:
            board = ((d >> 27 & 0b111) << 0) | ((d >> 36 & 0b111) << 3) | ((d >> 45 & 0b111) << 6)
            pass
        elif number == 4:
            board = ((d >> 30 & 0b111) << 0) | ((d >> 39 & 0b111) << 3) | ((d >> 48 & 0b111) << 6)
            pass
        elif number == 5:
            board = ((d >> 33 & 0b111) << 0) | ((d >> 42 & 0b111) << 3) | ((d >> 51 & 0b111) << 6)
            pass
        elif number == 6:
            board = ((d >> 54 & 0b111) << 0) | ((d >> 63 & 0b111) << 3) | ((d >> 72 & 0b111) << 6)
            pass
        elif number == 7:
            board = ((d >> 57 & 0b111) << 0) | ((d >> 66 & 0b111) << 3) | ((d >> 75 & 0b111) << 6)
            pass
        elif number == 8:
            board = ((d >> 60 & 0b111) << 0) | ((d >> 69 & 0b111) << 3) | ((d >> 78 & 0b111) << 6)
            pass
        return board


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
        self.lastMove = [-1, -1]
        self.board = GameBoard()
        self.currentGrid = -1

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
        if not (move >= 0 and move <= 80 and move == int(move) and (self.board.GetData() & (1 << move)) == 0):
            # print('{:b}'.format(self.board.GetData()), file=sys.stderr, flush=True)
            # print('{:b}'.format(1 << move), file=sys.stderr, flush=True)
            # print(str(self.board), file=sys.stderr, flush=True)
            assert True
        self.playerJustMoved = 1 if (self.playerJustMoved == 2 or self.playerJustMoved == 0) else 2
        self.board.Move(move, self.playerJustMoved)

    def GetMoves(self):
        """ Get all possible moves from this state.
        """
        ## Using first player, because we are only interested in a draw anyway
        return self.board.GetMoves()

    def GetResult(self, playerjm):
        """ Get the game result from the viewpoint of playerjm.
        """
        return self.board.GetResult(playerjm)
        # assert False  # Should not be possible to get here

    def __repr__(self):
        return str(self.board)


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
        s = sorted(self.childNodes, key=lambda c: c.wins / c.visits + math.sqrt(2 * math.log(self.visits) / c.visits))[
            -1]
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


turn_start = time.time()


def UCT(rootstate, itermax, verbose=False):
    """ Conduct a UCT search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.
        Assumes 2 alternating players (player 1 starts), with game results in the range [0.0, 1.0]."""
    global turn_start
    turn_start = time.time()
    start_time = turn_start

    rootnode = Node(state=rootstate)

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
            ## This is a place for improvement, here we can try to do a small simulation (just for the small grid)
            m = random.choice(node.untriedMoves)
            state.DoMove(m)
            node = node.AddChild(m, state)  # add child and descend tree

        # Rollout - this can often be made orders of magnitude quicker using a state.GetRandomMove() function
        steps = 1
        while state.GetMoves() != []:  # while state is non-terminal
            steps += 1
            m = random.choice(state.GetMoves())
            state.DoMove(m)

        # Backpropagate
        last_player = node.playerJustMoved
        result = (state.GetResult(node.playerJustMoved)) / steps
        while node != None:  # backpropagate from the expanded node and work back to the root node
            node.Update(result)  # state is terminal. Update node with result from POV of node.playerJustMoved
            result = result * (-1)
            node = node.parentNode

        cur_time = time.time()
        loop_time = (cur_time - turn_start) / loops
        # print("loop time:", loop_time)
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
        # print("hmm", loops)
        pass
        # print(rootstate)
        # print(rootnode.TreeToString(0))

    # print("Large loops", loops, file=sys.stderr, flush=True)
    # print("Large loops", loops)
    # print("Turn time:", time.time() - start_time, file=sys.stderr, flush=True)
    return sorted(sorted(rootnode.childNodes, key=lambda c: c.wins / c.visits), key=lambda c: c.wins)[
        -1].move  # return the move that was most visited


class UCTPlayer:
    def __init__(self, max_iterations):
        self.state = OXOState()
        self.playerNum = 1
        self.maxIterations = max_iterations
        self.initialized = False
        pass

    def get_move(self, opponentAction, validActions):
        if opponentAction[0] == opponentAction[1] == -1:
            self.playerNum = 2
        else:
            self.state.DoMove(opponentAction[0] + opponentAction[1] * 9)

        moves = self.state.GetMoves()
        # print([[m % 9, math.floor(m / 9)] for m in moves], file=sys.stderr, flush=True)
        move = None
        if len(validActions) > 0:
            m = None
            if not self.initialized:
                m = UCT(rootstate=self.state, itermax=995, verbose=True)
                self.initialized = True
            else:
                m = UCT(rootstate=self.state, itermax=self.maxIterations, verbose=True)
            # print(m)
            self.state.DoMove(m)
            move = [m % 9, math.floor(m / 9)]
        else:
            pass

        # print(str(self.state), file=sys.stderr, flush=True)

        return move

    # def getResult(self):
    #     result = self.state.GetResult(self.playerNum)
    #     if result > 0:
    #         return 1.0
    #     elif result <= 0:
    #         return 0
    #     else:
    #         return 0.5



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


import tictactoe
import ticplayer


def play_game():
    player1 = UCTPlayer(100)
    player2 = ticplayer.BasicPlayer()
    large = True
    global game_instance
    game_instance = tictactoe.Game(large, player1, player2)
    result = game_instance.play()
    # if result != 1 if player1.getResult() == 1.0 else 2:
    #     pass
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

# import matplotlib.pyplot as plt

def graph_things():
    games = 1000
    maximum_iters = 101
    iters_steps = 5

    # plt.axis([0, maximum_iters, 0, games])

    for max_iters in range(1, maximum_iters + 1, iters_steps):
        s = 0
        for i in range(games):
            r = UCTPlayGame(max_iters)
            s += 1 if r == 1 else 0.5 if r == 0 else 0
            # plt.pause(0.05)
            print(i + 1, s)

        # plt.scatter(max_iters, s)
        # plt.pause(0.05)
        print(s)

    # plt.show()


if __name__ == "__main__":
    """ Play a single game to the end using UCT for both players. 
    """

    evaluate_solution()
    # while True:
    # s = time.time()
    # print(play_game())
    # count = 1
    # iter_max = 10
    # s = time.time()
    # loop = 0;
    # for i in range(count):
    #     loop += 1
    # UCTPlayGame(10)
    #     print("Time elapsed avg (so far):", (time.time() - s) / loop)
    # print("Time elapsed avg:", (time.time() - s) / 1)
    # graph_things()

    # state = OXOState()  # uncomment to play OXO
    # state = NimState(15)  # uncomment to play Nim with the given number of starting chips
    # UCT(rootstate=state, itermax=1000000, verbose=True)  # player 1


## Last result 72.95

