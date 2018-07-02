import random
import math


def get_grid_from_cords(x, y):
    return int(math.floor(y/3)) * 3 + int(math.floor(x/3))

def get_offset_for_grid(number):
    return [
        number%3 * 3,
        int(math.floor(number/3)) * 3
    ]

class Game:
    def __init__(self, large, player1, player2):
        self.data = []
        self.large = large
        self.player1 = player1
        self.player2 = player2
        self.curPlayer = random.randint(1,2)
        self.turn = 0
        if self.large:
            self.activeGrid = -1
        else:
            self.activeGrid = 0
        self.lastMove = [-1,-1]
        if self.large:
            self.grids = []
            for x in range(9):
                self.grids.append(Grid())
        else:
            self.grids = [Grid()]

    def active_grid(self):
        return self.activeGrid

    def check_winner(self):
        if self.large:
            grid = Grid()
            grid.set_grid([[self.grids[0].check_winner(),self.grids[1].check_winner(), self.grids[2].check_winner()],
                           [self.grids[3].check_winner(), self.grids[4].check_winner(), self.grids[5].check_winner()],
                           [self.grids[6].check_winner(), self.grids[7].check_winner(), self.grids[8].check_winner()]])
            return grid.check_winner()
        else:
            return self.grids[0].check_winner()
        return 0

    def get_available_actions(self):
        actions = []
        if self.check_winner() > 0:
            return []
        if self.activeGrid != -1:
            actions = self.grids[self.activeGrid].get_available_actions(self.activeGrid)
        if len(actions) == 0:
            # here we need to return all possible actions
            actions = []
            for i in range(len(self.grids)):
                actions.extend(self.grids[i].get_available_actions(i))

        return actions

    def printGrid(self):
        print('###############')
        print(self.lastMove)
        if self.large:
            grid = []
            for row in range(9):
                grid.append([0]*9)
                for col in range(9):
                    gridNum = get_grid_from_cords(col, row)
                    grid_col = col%3
                    grid_row = row%3
                    grid[row][col] = self.grids[gridNum].get_grid()[grid_row][grid_col]
            for row in grid:
                print(row)
        else:
            for row in range(3):
                print(self.grids[0].get_grid()[row])
        print('---------------')
        return 0

    def play(self, debug=False):
        while self.check_winner() == 0:
            self.turn += 1
            actions = self.get_available_actions()
            if len(actions) == 0:
                # check who got more little wins
                score = 0
                for grid in self.grids:
                    if grid.check_winner() == 1:
                        score += 1
                    elif grid.check_winner() == 2:
                        score -= 1
                if score > 0:
                    return 1

                if score < 0:
                    return 2

                return 0
            else:
                if self.curPlayer == 1:
                    self.lastMove = self.player1.get_move(self.lastMove, actions)
                else:
                    self.lastMove = self.player2.get_move(self.lastMove, actions)

                gridNum = get_grid_from_cords(self.lastMove[0], self.lastMove[1])
                gridNumOffset = get_offset_for_grid(gridNum)

                self.grids[gridNum].play(self.curPlayer,
                                                 self.lastMove[0] - gridNumOffset[0],
                                                 self.lastMove[1] - gridNumOffset[1])

                self.curPlayer = 1 if self.curPlayer == 2 else 2
                if self.large:
                    self.activeGrid = self.lastMove[0]%3 + self.lastMove[1]%3 * 3

            if debug:
                self.printGrid()

        return self.check_winner()



class Grid:
    def __init__(self):
        self.grid = [[0,0,0],
                     [0,0,0],
                     [0,0,0]]

    def set_grid(self, grid):
        self.grid = grid

    def get_grid(self):
        return self.grid

    def get_available_actions(self, activeGrid):
        actions = []
        if self.check_winner() == 0:
            for row in range(len(self.grid)):
                for col in range(len(self.grid[row])):
                    if self.grid[row][col] == 0:
                        gridOffset = get_offset_for_grid(activeGrid)
                        actions.append([col + gridOffset[0], row + gridOffset[1]])
        return actions

    def play(self, player, col, row):
        self.grid[row][col] = player

    def check_winner(self):
        for i in range(3):
            # check rows
            if self.grid[i][0] > 0 and self.grid[i][0] == self.grid[i][1] and self.grid[i][0] == self.grid[i][2]:
                return self.grid[i][0]
            # check cols
            if self.grid[0][i] > 0 and self.grid[0][i] == self.grid[1][i] and self.grid[1][i] == self.grid[2][i]:
                return self.grid[0][i]
        # check diagnoal 1
        if self.grid[0][0] > 0 and self.grid[0][0] == self.grid[1][1] and self.grid[0][0] == self.grid[2][2]:
            return self.grid[0][0]
        # check diagnoal 2
        if self.grid[2][0] > 0 and self.grid[2][0] == self.grid[1][1] and self.grid[2][0] == self.grid[0][2]:
            return self.grid[2][0]

        return 0

