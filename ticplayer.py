import math
import neat
import pickle
import random
import copy

class Player:
    def __init__(self, file):
        self.inputs = [0] * 81
        self.net = pickle.load(open(file, "rb"))
        self.large = False

    def add_input(self, isMe, x, y):
        if self.large:
            self.inputs[x + y * 9] = 1 if isMe else -1
        else:
            self.inputs[x + y * 3] = 1 if isMe else -1

    def get_move(self, opponentAction, validActions):
        if opponentAction[0] >= 0 and opponentAction[1] >= 0:
            self.add_input(False, opponentAction[0], opponentAction[1])

        result_raw = self.net.activate(self.inputs[0:9])
        bestAction = None
        bestScore = -999999999

        # x = min(max(0,int(result_raw[0] * 9)),8)
        # y = min(max(0,int(result_raw[1] * 9)),8)
        #
        #
        # for action in validActions:
        #     actionScore = abs(action[0] - x) * abs(action[1] -y)

        for action in validActions:
            actionScore = result_raw[action[0] + action[1]*3]
            #actionScore = result_raw[int(0)]
            if actionScore > bestScore:
                bestScore = actionScore
                bestAction = action

        self.add_input(True, bestAction[0], bestAction[1])

        return bestAction

class BasicPlayer:
    def __init__(self):
        pass

    def get_move(self, opponentAction, validActions):
        if len(validActions) > 0:
            return random.choice(validActions)
        else:
            return None

def get_grid_from_cords(x, y):
    return int(math.floor(y/3)) * 3 + int(math.floor(x/3))

def get_offset_for_grid(number):
    return [
        number%3 * 3,
        int(math.floor(number/3)) * 3
    ]

## only small grid
class CombinedPlayer:
    def __init__(self, file, ignoreNet = False):
        self.inputs = [0] * 81
        self.net = None
        if not ignoreNet:
            self.net = pickle.load(open(file, "rb"))
        self.large = False
        self.grid = [[0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,0]]
        pass

    def get_inputs(self, gridNumber):
        inputs = []
        off = get_offset_for_grid(gridNumber)
        for row in range(off[1], 3 + off[1]):
            for col in range(off[0], 3 + off[0]):
                inputs.append(self.grid[row][col])
        return inputs

    def add_input(self, isMe, x, y):
        self.grid[y][x] = 1 if isMe else -1

    def getGrid(self, gridNumber):
        return self.getGridSubset(gridNumber, self.grid)

    def getGridSubset(self, subsetNumber, grid):
        off = get_offset_for_grid(subsetNumber)
        tempGrid = [[0,0,0],[0,0,0],[0,0,0]]
        for row in range(0, 3):
            for col in range(0, 3):
                tempGrid[row][col] = grid[row + off[1]][col + off[0]]
        return tempGrid

    def is_winning_move(self, isMe, move):
        gridNumber = get_grid_from_cords(move[0], move[1])
        off = get_offset_for_grid(gridNumber)
        tempGrid = self.getGrid(gridNumber)

        tempGrid[move[1] - off[1]][move[0] - off[0]] = 1 if isMe else -1
        return self.check_winner(tempGrid)

    def check_winner(self, grid):
        # print("C", grid)
        for i in range(3):
            # check rows
            if grid[i][0] != 0 and grid[i][0] == grid[i][1] and grid[i][0] == grid[i][2]:
                return grid[i][0]
            # check cols
            if grid[0][i] != 0 and grid[0][i] == grid[1][i] and grid[1][i] == grid[2][i]:
                return grid[0][i]
        # check diagnoal 1
        if grid[0][0] != 0 and grid[0][0] == grid[1][1] and grid[0][0] == grid[2][2]:
            return grid[0][0]
        # check diagnoal 2
        if grid[2][0] != 0 and grid[2][0] == grid[1][1] and grid[2][0] == grid[0][2]:
            return grid[2][0]

        return 0

    def isMoveSafe(self, move):
        gridAfterMove = copy.deepcopy(self.grid)
        gridAfterMove[move[1]][move[0]] = 1

        gridsToCheck = []
        nextGridNumber = move[0]%3 + move[1]%3 * 3
        nextGrid = self.getGridSubset(nextGridNumber, gridAfterMove)
        if self.check_winner(nextGrid) == 0:
            gridsToCheck.append(nextGrid)
        else:
            for i in range(9):
                gridsToCheck.append(self.getGridSubset(i, gridAfterMove))

        for grid in gridsToCheck:
            for x in range(3):
                for y in range(3):
                    if grid[y][x] == 0:
                        tempGrid = copy.deepcopy(grid)
                        ## check for opp
                        tempGrid[y][x] = -1
                        if self.check_winner(tempGrid) != 0:
                            return False
                        ## check for me
                        tempGrid[y][x] = 1
                        if self.check_winner(tempGrid) != 0:
                            return False

        return True

    def isLosingMove(self, move, grid):
        gridAfterMove = copy.deepcopy(self.grid)
        gridAfterMove[move[1]][move[0]] = 1

        gridsToCheck = []
        nextGridNumber = move[0]%3 + move[1]%3 * 3
        nextGrid = self.getGridSubset(nextGridNumber, gridAfterMove)
        if self.check_winner(nextGrid) == 0:
            gridsToCheck.append(nextGrid)
        else:
            for i in range(9):
                gridsToCheck.append(self.getGridSubset(i, gridAfterMove))

        for i in range(len(gridsToCheck)):
            grid = gridsToCheck[i]
            for x in range(3):
                for y in range(3):
                    if grid[y][x] == 0:
                        off = get_offset_for_grid(i)
                        if self.isMoveFinal([x + off[0], y + off[1]], gridAfterMove, -1) == -1:
                            return True

        return False

    def isMoveFinal(self, move, grid, player):
        gridAfterMove = copy.deepcopy(grid)
        gridAfterMove[move[1]][move[0]] = player

        gridsToCheck = []
        nextGridNumber = move[0]%3 + move[1]%3 * 3
        nextGrid = self.getGridSubset(nextGridNumber, gridAfterMove)

        if self.check_winner(nextGrid) == 0:
            gridsToCheck.append(nextGrid)
        else:
            for i in range(9):
                gridsToCheck.append(self.getGridSubset(i, gridAfterMove))

        largeGrid = [[0,0,0],[0,0,0],[0,0,0]]
        for i in range(9):
            row = int(math.floor(i / 3))
            col = i % 3
            largeGrid[row][col] = self.check_winner(self.getGridSubset(i, gridAfterMove))

        return self.check_winner(largeGrid)

    def get_move(self, opponentAction, validActions):
        # print("1", self.grid)

        if opponentAction[0] >= 0 and opponentAction[1] >= 0:
            self.add_input(False, opponentAction[0], opponentAction[1])

        # print("2", self.grid)


        bestAction = None

        # check if we can end the game
        if bestAction is None:
            for action in validActions:
                if self.isMoveFinal(action, self.grid, 1) == 1 and self.large:
                    bestAction = action
                    # print("My winning move", action)
                    break

        # remove valid actions that make the opp win
        safeActions = []
        if bestAction is None:
            for action in validActions:
                if not self.isLosingMove(action, self.grid):
                    safeActions.append(action)

        # only safe moves
        if bestAction is None:
            for action in safeActions:
                if (self.is_winning_move(True, action) == 1):
                    if self.isMoveSafe(action) or not self.large:
                        bestAction = action
                        # print("My winning move", action)
                        break

        if bestAction is None:
            for action in safeActions:
                if (self.is_winning_move(False, action) == -1):
                    if self.isMoveSafe(action) or not self.large:
                        bestAction = action
                        # print("Opp winning move", action)
                        break

        ## check for safe moves
        if bestAction is None and self.net is not None:
            bestScore = -999999999

            for action in safeActions:
                if self.isMoveSafe(action) or not self.large:
                    gridNumber = get_grid_from_cords(action[0], action[1])
                    off = get_offset_for_grid(gridNumber)

                    result_raw = self.net.activate(self.get_inputs(gridNumber))
                    actionScore = result_raw[(action[0] - off[0]) + (action[1] - off[1])*3]
                    # actionScore = result_raw[int(0)]
                    if actionScore > bestScore:
                        bestScore = actionScore
                        bestAction = action

        # do not check for safe moves
        if bestAction is None:
            for action in safeActions:
                if (self.is_winning_move(True, action) == 1):
                    bestAction = action
                    print("My winning move", action)
                    break

        if bestAction is None:
            for action in safeActions:
                if (self.is_winning_move(False, action) == -1):
                    bestAction = action
                    print("Opp winning move", action)
                    break

        ## do not check for safe moves
        if bestAction is None and self.net is not None:
            bestScore = -999999999

            gridNumber = get_grid_from_cords(action[0], action[1])
            off = get_offset_for_grid(gridNumber)

            result_raw = self.net.activate(self.get_inputs(gridNumber))
            actionScore = result_raw[(action[0] - off[0]) + (action[1] - off[1]) * 3]
            # actionScore = result_raw[int(0)]
            if actionScore > bestScore:
                bestScore = actionScore
                bestAction = action

        if bestAction is None:
            # if self.net is not None:
            #     print("going random", safeActions)
            bestAction = random.choice(validActions)

        # print("3", self.grid)
        self.add_input(True, bestAction[0], bestAction[1])

        # print("4", self.grid)
        return bestAction

## only small grid
class BetterPlayer:
    def __init__(self):
        self.grid = [[0,0,0],[0,0,0],[0,0,0]]
        pass

    def add_input(self, isMe, x, y):
        self.grid[y][x] = 1 if isMe else 2

    def is_winning_move(self, isMe, move):
        tempGrid = copy.deepcopy(self.grid)
        tempGrid[move[1]][move[0]] = 1 if isMe else 2
        return self.check_winner(tempGrid)

    def check_winner(self, grid):
        # print("C", grid)
        for i in range(3):
            # check rows
            if grid[i][0] > 0 and grid[i][0] == grid[i][1] and grid[i][0] == grid[i][2]:
                return grid[i][0]
            # check cols
            if grid[0][i] > 0 and grid[0][i] == grid[1][i] and grid[1][i] == grid[2][i]:
                return grid[0][i]
        # check diagnoal 1
        if grid[0][0] > 0 and grid[0][0] == grid[1][1] and grid[0][0] == grid[2][2]:
            return grid[0][0]
        # check diagnoal 2
        if grid[2][0] > 0 and grid[2][0] == grid[1][1] and grid[2][0] == grid[0][2]:
            return grid[2][0]

        return 0

    def get_move(self, opponentAction, validActions):
        # print("1", self.grid)

        if opponentAction[0] >= 0 and opponentAction[1] >= 0:
            self.add_input(False, opponentAction[0], opponentAction[1])

        # print("2", self.grid)


        bestAction = None
        for action in validActions:
            if (self.is_winning_move(True, action) == 1):
                bestAction = action
                # print("My winning move", action)
                break

        if bestAction is None:
            for action in validActions:
                if (self.is_winning_move(False, action) == 2):
                    bestAction = action
                    # print("Opp winning move", action)
                    break

        if bestAction is None:
            bestAction = random.choice(validActions)

        # print("3", self.grid)
        self.add_input(True, bestAction[0], bestAction[1])

        # print("4", self.grid)
        return bestAction