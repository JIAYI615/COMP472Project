from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
import requests

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4

class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker

class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3

##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health : int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table : ClassVar[list[list[int]]] = [
        [3,3,3,3,1], # AI
        [1,1,6,1,1], # Tech
        [9,6,1,6,1], # Virus
        [3,3,3,3,1], # Program
        [1,1,1,1,1], # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table : ClassVar[list[list[int]]] = [
        [0,1,1,0,0], # AI
        [3,0,0,3,3], # Tech
        [0,0,0,0,0], # Virus
        [0,0,0,0,0], # Program
        [0,0,0,0,0], # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0

    def mod_health(self, health_delta : int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"
    
    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()
    
    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount

##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row : int = 0
    col : int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
                coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
                coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()
    
    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()
    
    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist,self.row+1+dist):
            for col in range(self.col-dist,self.col+1+dist):
                yield Coord(row,col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1,self.col)
        yield Coord(self.row,self.col-1)
        yield Coord(self.row+1,self.col)
        yield Coord(self.row,self.col+1)

    @classmethod
    def from_string(cls, s : str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src : Coord = field(default_factory=Coord)
    dst : Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()
    
    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row,self.dst.row+1):
            for col in range(self.src.col,self.dst.col+1):
                yield Coord(row,col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0,col0),Coord(row1,col1))
    
    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0,0),Coord(dim-1,dim-1))
    
    @classmethod
    def from_string(cls, s : str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth : int | None = 4
    min_depth : int | None = 2
    max_time : float | None = 5.0
    game_type : GameType = GameType.AttackerVsDefender
    alpha_beta : bool = True
    max_turns : int | None = 100
    randomize_moves : bool = True
    broker : str | None = None
    evaluation: int | None = 0

##############################################################################################################

@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth : dict[int,int] = field(default_factory=dict)
    total_seconds: float = 0.0
    evaluations_depth : dict[str,int] = field(default_factory=dict)

##############################################################################################################

@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    last_move : CoordPair = None
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker
    turns_played : int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=Player.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=Player.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=Player.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=Player.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def is_valid_move(self, coords : CoordPair) -> bool:
        """Validate a move expressed as a CoordPair. TODO: WRITE MISSING CODE!!!"""
        
        #check is the entered current unit place and the entered target unit are valid
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        
        unit = self.get(coords.src) #current unit
        unit2 = self.get(coords.dst) #destination unit
        
        # check if the user enters an empty coord and if the user tries to move other user's coord
        if unit is None or unit.player != self.next_player:
            return False
        
        # If the user wants to self destroy a coord, always valid:
        if coords.src.row == coords.dst.row and coords.src.col == coords.dst.col:
            return True
        
        # Check if the dst and the src are next to each other:
        if not (abs(coords.src.row-coords.dst.row) ==1 and abs(coords.src.col-coords.dst.col) ==0):
            if not (abs(coords.src.row-coords.dst.row) ==0 and abs(coords.src.col-coords.dst.col) ==1):
                return False
        
        # if the current player is attacker
        if unit.player.name == "Attacker":
            # print("------ATTACKER------")
            #check if the target coord is empty
            if unit2 is None: #if the target coord is empty
                #collect the coords in adjacent except for the target coord
                coordAround = coords.src.iter_adjacent()
                isInCombat = False
                for i in coordAround:
                     # if i is out of board, skip
                    if not self.is_valid_coord(i):
                        continue
                    # if i is empty, skip
                    if self.get(i) is None:
                        continue
                    # if find enemy's unit, info needed get, break
                    if self.get(i).player.name != unit.player.name:
                        isInCombat = True
                        break
                if isInCombat:
                    if unit.type.name == "Virus":   #virus can go no matter is in combat or not
                        return True
                    else:
                        return False    #Sorry, AI, Firewall, and Program can't move when in combat
                else:   #no combat
                    if unit.type.name == "Virus":
                        return True
                    else:   #need to check if it's going up/left or not
                        if coords.src.row < coords.dst.row or coords.src.col < coords.dst.col:
                            return False    #invalid if going down/right
                        else:
                            return True                   
            else:   #if the target coord is not empty, so it's either attack or repair
                if unit2.player.name != unit.player.name:   #So it's an attack
                    return True     #attack is always valid right?
                else:   #So it tries to repair, need to check if it's possible to perform repair
                    if unit.type.name == "AI":   #Only tech and AI can repair, attacker doesn't have tech, so only AI can repair
                        if unit2.type.name == "Virus":  # Attacker's AI can only cure virus, check if it's the right type
                            if unit2.health == 9:   #correct type, but very healthy....no need to repair
                                return False
                            else:   #do need repair
                                return True
                        else:   #other type can't be cured
                            return False
                       
                    else:   #The type is not AI, you can't repair anyways
                        return False

        # if the current player is defender:
        if unit.player.name == "Defender":
            # print("-----DEFENDER-----")
            if unit2 is None: #if the target coord is empty
                #collect the coords in adjacent except for the target coord
                coordAround = coords.src.iter_adjacent()
                isInCombat = False
                for i in coordAround:
                     # if i is out of board, skip
                    if not self.is_valid_coord(i):
                        continue
                    # if i is empty, skip
                    if self.get(i) is None:
                        continue
                    # if find enemy's unit, info needed get, break
                    if self.get(i).player.name != unit.player.name:
                        isInCombat = True
                        break
                if isInCombat:
                    if unit.type.name == "Tech":   #Tech can go no matter is in combat or not
                        return True
                    else:
                        return False    #Sorry, AI, Firewall, and Program can't move when in combat
                else:   #no combat
                    if unit.type.name == "Tech":
                        return True
                    else:   #need to check if it's going down/right or not
                        if coords.src.row > coords.dst.row or coords.src.col > coords.dst.col:
                            return False    #invalid if going up/left
                        else:
                            return True                   
            else:   #if the target coord is not empty, so it's either attack or repair
                if unit2.player.name != unit.player.name:   #So it's an attack
                    return True     #attack is always valid right?
                else:   #So it tries to repair, need to check if it's possible to perform repair
                    if unit.type.name == "AI" or unit.type.name == "Tech":   #Only tech and AI can repair, defender has both
                        if unit.type.name == "AI":  #if AI's gonna repair:
                            if unit2.type.name == "Tech":   #Defender's AI can only cure tech
                                if unit2.health == 9:   #Very healthy....no need to repair
                                    return False
                                else:   #do need repair
                                    return True
                        else:   #if tech's gonna repair
                            if unit2.type.name == "Program" or unit2.type.name == "AI" or unit2.type.name == "Firewall":    #only AI, firewall, and program can be cured by tech
                                if unit2.health == 9:   #Very healthy....no need to repair
                                    return False
                                else:   #do need repair
                                    return True
                    else:   #The type is not AI or tech, you can't repair anyways
                        return False

    def perform_move(self, coords : CoordPair) -> Tuple[bool,str]:
        """Validate and perform a move expressed as a CoordPair. TODO: WRITE MISSING CODE!!!"""
        if self.is_valid_move(coords):
            if self.get(coords.dst) is None: #if move to an empty coord
            # print("-----MOVE FORM TO-----"+coords.to_string())
                unit1 = self.get(coords.src)
                unit2 = self.get(coords.dst)
                srcrow = str(coords.src.row)
                srccol= str(coords.src.col)
                dstrow = str(coords.dst.row)
                dstcol= str(coords.dst.col)
                self.set(coords.dst,self.get(coords.src))
                self.set(coords.src,None)
                successString = self.next_player.name + " moves " + unit1.type.name + " from (" + srcrow + " , "+ srccol +") to " "(" + dstrow + " , "+ dstcol +")" 
                return (True, successString)
            
            elif coords.src ==coords.dst: #if want to destroy it self
                unit1 = self.get(coords.src)
                srcrow = str(coords.src.row)
                srccol= str(coords.src.col)
                for i in coords.src.iter_range(1):
                    #if the place of the i is out of boarder
                    if not self.is_valid_coord(i):
                        continue
                    # if i is empty, skip
                    if self.get(i) is None:
                        continue

                    #DON'T REMOVE!! This check is super important, I don't know what but without this we'll have bugs in minimax
                    if i.row == coords.src.row and i.col == coords.src.col:
                        continue

                    #then change the health
                    # print(str(i.row) + " , " + str(i.col))
                    # health_change = self.get(coords.src).damage_amount(self.get(i))
                    # self.mod_health(i, -health_change)
                    self.mod_health(i, -2)
                # print(self.get(coords.src).type)
                self.get(coords.src).health = 0
                self.remove_dead(coords.src)
                # if self.get(coords.src).type == UnitType.AI:
                #     if self.get(coords.src).player == Player.Attacker:
                #         self._attacker_has_ai = False
                successString = self.next_player.name + " destroy " + unit1.type.name + " at (" + srcrow + " , "+ srccol + ")"
                return (True, successString)
            
            elif self.get(coords.src).player.name == self.get(coords.dst).player.name: #if it's repair
                unit1 = self.get(coords.src)
                unit2 = self.get(coords.dst)
                srcrow = str(coords.src.row)
                srccol= str(coords.src.col)
                dstrow = str(coords.dst.row)
                dstcol= str(coords.dst.col)
                health_change = self.get(coords.src).repair_amount(self.get(coords.dst))
                self.mod_health(coords.dst, health_change)
                successString = self.next_player.name + " used unit " + unit1.type.name +" at (" +srcrow + " , "+srccol+ ") repair the unit " + unit2.type.name + " at (" + dstrow + " , "+dstcol +")" 
                return (True, successString)
            
            elif self.get(coords.src).player.name != self.get(coords.dst).player.name: #if it's attack
                unit1 = self.get(coords.src)
                unit2 = self.get(coords.dst)
                srcrow = str(coords.src.row)
                srccol= str(coords.src.col)
                dstrow = str(coords.dst.row)
                dstcol= str(coords.dst.col)
                health_change1 = self.get(coords.src).damage_amount(self.get(coords.dst))
                health_change2 = self.get(coords.dst).damage_amount(self.get(coords.src))
                self.mod_health(coords.dst, -health_change1)
                self.mod_health(coords.src, -health_change2)
                self.remove_dead(coords.dst)
                self.remove_dead(coords.src)
                successString = self.next_player.name + " used unit " + unit1.type.name +" at (" +srcrow + " , "+ srccol+ ") attack the unit " + unit2.type.name +" at (" + dstrow + " , "+ dstcol +" )" 
                return (True, successString)
        return (False,"invalid move")

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output
    
    def print_board(self) -> str:
        dim = self.options.dim
        coord = Coord()
        output = ""
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()
    
    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                self.last_move = coords
                return coords
            else:
                print('Invalid coordinates! Try again.')
    
    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.perform_move(mv)
                    print(f"Broker {self.next_player.name}: ",end='')
                    print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success,result) = self.perform_move(mv)
                if success:
                    print(f"Player {self.next_player.name}: ",end='')
                    print(result)
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is not None:
            (success,result) = self.perform_move(mv)
            if success:
                self.last_move = mv
                print(f"Computer {self.next_player.name}: ",end='')
                print(result)
                self.next_turn()
        #if the ai fail to find a move in the max time limit, AI lose
        else:
            winner = self.next_player.next()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        elif self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker    
        elif self._defender_has_ai:
            return Player.Defender
        else:
            return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0], 1)
        else:
            return (0, None, 0)

    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
        start_time = datetime.now()
        # (score, move, avg_depth) = self.random_move()
        # python3 ai_wargame_skeleton.py --game_type auto --max_depth 2 --alpha_beta true
        i = 0
        while i <= self.options.max_depth:
            self.stats.evaluations_per_depth[i] = 0
            i +=1
        self.stats.evaluations_per_depth[0]=1
        self.stats.evaluations_depth["leavesNum"] = 0
        self.stats.evaluations_depth["totalDepth"] = 0

        # (score, move, avg_depth) = self.miniMax(self.clone(), 0, self.next_player.value,start_time, True)
        #need to be changed when alphaBeta is added
        if self.options.alpha_beta:
            (score, move, avg_depth) = self.alphaBeta(self.clone(), 0, self.next_player.value,start_time, self.next_player == Player.Attacker, MIN_HEURISTIC_SCORE, MAX_HEURISTIC_SCORE)
        else:
            (score, move, avg_depth) = self.miniMax(self.clone(), 0, self.next_player.value,start_time, self.next_player == Player.Attacker)
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        f.write("This is for : " + str(self.next_player.name)+'\n')
        f.write("Heuristic score: " + str(score)+'\n')
        f.write("Average recursive depth: " +str(avg_depth)+'\n')
        f.write("Evals per depth: ")
        print("THIS IS FOR : " + str(self.next_player.name))
        print(f"Heuristic score: {score}")
        print(f"Average recursive depth: {avg_depth:0.1f}")
        print(f"Evals per depth: ",end='')
        
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            f.write(" "+str(k)+": "+str(self.stats.evaluations_per_depth[k]))
            print(f"{k}:{self.stats.evaluations_per_depth[k]} ",end='')
        print()
        
        total_evals = sum(self.stats.evaluations_per_depth.values())
        f.write('\n'+"Cumulative evals: " + str(total_evals) +'\n')
        print("Cumulative evals: " + str(total_evals))
        
        f.write("Cumulative % evals by depth: " +'\n')
        print("Cumulative % evals by depth: " )
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            f.write(" "+str(k)+": "+str(self.stats.evaluations_per_depth[k]/total_evals))
            print(f"{k}:{self.stats.evaluations_per_depth[k]/total_evals*100:.6f}%  ",end='')
        
        averageBranchingFactor = total_evals/(total_evals-self.stats.evaluations_depth["leavesNum"]+1)
        f.write('\n'+"Average branching factor:: " + str(averageBranchingFactor) +'\n')
        print()
        print("Average branching factor:: " + str(averageBranchingFactor))
        f.write("Total leaf Number: " + str(self.stats.evaluations_depth["leavesNum"])+'\n')
        print("Total leaf NUmber: "+ str(self.stats.evaluations_depth["leavesNum"]))
        
        if self.stats.total_seconds > 0:
            f.write('\n'+"Eval perf.: " + str(total_evals/self.stats.total_seconds/1000) +"k/s"+'\n')
            print(f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
        
        f.write("Elapsed time: " +str(elapsed_seconds) +"s"+'\n\n')
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        return move
    
    def miniMax(self, game : Game, depth : int, playerValue : int, start_time, isMax:bool)-> Tuple[int, CoordPair | None, float]:
        #if reach the end of the adversarial tree or find a goal state no matter who wins, no need to generate children, want to save time
        if depth == self.options.max_depth or game.is_finished():
            self.stats.evaluations_depth["leavesNum"] +=1
            self.stats.evaluations_depth["totalDepth"] += (depth)
            avg_depth = self.stats.evaluations_depth["totalDepth"]/self.stats.evaluations_depth["leavesNum"]
            if self.options.evaluation == 0:
                evaluation_score = game.evaluate0(playerValue)
            elif self.options.evaluation == 1:
                evaluation_score = game.evaluate1(playerValue)
            elif self.options.evaluation == 2:
                evaluation_score = game.evaluate2(playerValue)
            return (evaluation_score, None, avg_depth)
        
        #this is the Max layer
        if isMax:
            best_score = MIN_HEURISTIC_SCORE
            best_move = None
            avg_depth = 0
            random_move_candidates = list(game.move_candidates())
            random.shuffle(random_move_candidates)
            newGame= game.clone()
            for i in random_move_candidates:
            # for i in game.move_candidates():
                if (datetime.now() - start_time).total_seconds() > self.options.max_time:   #if AI exceed the time
                    return (best_score, best_move, avg_depth)
                newGame = game.clone()
                newGame.perform_move(i)
                newGame.next_turn()
                newGame.stats.evaluations_per_depth[depth+1] += 1
                (eval, move, avg_depth) = self.miniMax(newGame.clone(), depth+1, playerValue,start_time, False)
                if eval > best_score:   #update the max value
                    best_score = max(eval, best_score)
                    best_move = i
            return (best_score, best_move, avg_depth)   #return the max value
        
        #this is the min layer
        else:
            best_score = MAX_HEURISTIC_SCORE
            best_move = None
            avg_depth = 0
            random_move_candidates = list(game.move_candidates())
            random.shuffle(random_move_candidates)
            newGame = game.clone()
            for i in random_move_candidates:
            # for i in game.move_candidates():
                if (datetime.now() - start_time).total_seconds() > self.options.max_time:   #if AI exceed the time
                    return (best_score, best_move, avg_depth)
                newGame = game.clone()
                newGame.perform_move(i)
                newGame.next_turn()
                newGame.stats.evaluations_per_depth[depth+1] += 1
                (eval, move, avg_depth) = self.miniMax(newGame.clone(), depth+1, playerValue,start_time, True)
                if eval < best_score:   #update the best value
                    best_score = min(eval, best_score)
                    best_move = i           
            return (best_score, best_move, avg_depth)   #return the min value
        
    def alphaBeta(self, game : Game, depth : int, playerValue : int, start_time, isMax:bool, alpha: int, beta : int)-> Tuple[int, CoordPair | None, float]:
        if depth == self.options.max_depth or game.is_finished():
            self.stats.evaluations_depth["leavesNum"] +=1
            self.stats.evaluations_depth["totalDepth"] += (depth)
            avg_depth = self.stats.evaluations_depth["totalDepth"]/self.stats.evaluations_depth["leavesNum"]
            if self.options.evaluation == 0:
                evaluation_score = game.evaluate0(playerValue)
            elif self.options.evaluation == 1:
                evaluation_score = game.evaluate1(playerValue)
            elif self.options.evaluation == 2:
                evaluation_score = game.evaluate2(playerValue)
            return (evaluation_score, None, avg_depth)
        if isMax:
            best_score = MIN_HEURISTIC_SCORE
            best_move = None
            avg_depth = 0
            random_move_candidates = list(game.move_candidates())
            random.shuffle(random_move_candidates)
            newGame= game.clone()
            for i in random_move_candidates:
                if (datetime.now() - start_time).total_seconds() > self.options.max_time:   #if AI exceed the time
                    return (best_score, best_move, avg_depth)
                newGame = game.clone()
                newGame.perform_move(i)
                newGame.next_turn()
                newGame.stats.evaluations_per_depth[depth+1] += 1
                (eval, move, avg_depth) = self.alphaBeta(newGame.clone(), depth+1, playerValue ,start_time, False, alpha, beta)
                print('max:\neval:'+str(eval)+' move:'+str(move)+' avg_depth:'+str(avg_depth))
                temp_score = min(best_score, eval)
                temp_beta = min(beta, temp_score)
                if (beta <= alpha):
                    print('break max')
                    break
                best_move = i
                beta = temp_beta
                best_score = temp_score
            return (best_score, best_move, avg_depth)   #return the max value
        else:
            best_score = MAX_HEURISTIC_SCORE
            best_move = None
            avg_depth = 0
            random_move_candidates = list(game.move_candidates())
            random.shuffle(random_move_candidates)
            newGame = game.clone()
            for i in random_move_candidates:
            # for i in game.move_candidates():
                if (datetime.now() - start_time).total_seconds() > self.options.max_time:   #if AI exceed the time
                    return (best_score, best_move, avg_depth)
                newGame = game.clone()
                newGame.perform_move(i)
                newGame.next_turn()
                newGame.stats.evaluations_per_depth[depth+1] += 1
                (eval, move, avg_depth) = self.alphaBeta(newGame.clone(), depth+1, playerValue,start_time, True, alpha, beta)
                print('min:\neval:'+str(eval)+' move:'+str(move)+' avg_depth:'+str(avg_depth))
                temp_score = min(best_score, eval)
                temp_beta = min(beta, temp_score)
                if (beta <= alpha):
                    print('break min')
                    break
                best_move = i
                beta = temp_beta
                best_score = temp_score     
            return (best_score, best_move, avg_depth)   #return the min value

    
    def evaluate0(self, player : int) -> float:
        attacker_num = 0
        defender_num = 0
        for i in self.player_units(Player.Attacker):
            if i[1].type.name == "AI":
                attacker_num = attacker_num + 9999
            else:
                attacker_num = attacker_num + 3
        for i in self.player_units(Player.Defender):
            if i[1].type.name == "AI":
                defender_num  = defender_num  + 9999
            else:
                defender_num  = defender_num  + 3
        #attacker's value is 0, defender's value is 1
        if player == 0:
            return attacker_num-defender_num
        if player == 1:
            return defender_num-attacker_num
        
    #function to get the player's ai position, will be used in evaluation1
    def get_ai_position(self,player:Player)-> Tuple[Coord,Unit]:
        for i in self.player_units(player):
            if i[1].type.name == "AI":
                return i
    
    '''
    The evaluate function 1 is designed based on the distance between units and the ai. It's is assumed that
    each players want to make units which are good at attacking as close as possible to the other player's ai
    and place the units which are good at defending as close as possible to their own ai.
    '''
    def evaluate1(self, player : int) -> float: #evaluate the state by calculating the distance
        if (not self._attacker_has_ai) and (not self._defender_has_ai): #when the AIs are destroyed at the same time
            if player == 0: #if it's attacker, attacker loses
                return -9999
            if player == 1: #if it's defender, defender wins
                return 9999
            
        if (not self._attacker_has_ai) and self._defender_has_ai: #defender has AI and attacker doesn't
            if player == 0: #if it's attacker, attacker loses
                return -9999
            if player == 1: #if it's defender, defender wins
                return 9999
            
        if self._attacker_has_ai and (not self._defender_has_ai): #attacker has ai and defender doesn't
            if player == 0: #if it's attacker, attacker wins
                return 9999
            if player == 1: #if it's defender, defender loses
                return -9999
            
        #So both the attacker and the defender have ai, calculate the position numbers:
        attacker_attack_position = 0 #how far are attacker's virus and programs away from defender's ai
        attacker_defend_position = 0 #how far is attacker's firewall away from its own ai
        defender_attack_position = 0 #how far are defender's programs away from attacker's ai
        defender_defend_position = 0 #how far is defender's firewall away from its own ai
        attacker_ai = self.get_ai_position(Player.Attacker)[0] #get the attacker ai coord
        defender_ai = self.get_ai_position(Player.Defender)[0] #get the defender ai coord
        tech_turn =0 
        
        for i in self.player_units(Player.Attacker):
            if i[1].type.name == "Virus":
                attacker_attack_position += -61
                attacker_attack_position += 6*(abs(i[0].row - defender_ai.row) + abs(i[0].col - defender_ai.col))
                
            elif i[1].type.name == "Program":
                attacker_attack_position += -31
                attacker_attack_position += 3*(abs(i[0].row - defender_ai.row) + abs(i[0].col - defender_ai.col))
                
            elif i[1].type.name == "Firewall":
                attacker_defend_position += -11
                attacker_defend_position += abs(i[0].row -attacker_ai.row) + abs(i[0].col - attacker_ai.col)
        
        for i in self.player_units(Player.Defender):
            if i[1].type.name == "Firewall":
                defender_defend_position += -101
                defender_defend_position += 10*(abs(i[0].row - defender_ai.row) + abs(i[0].col - defender_ai.col))

            elif i[1].type.name == "Tech":
                if tech_turn == 0:
                    defender_defend_position += -31
                    defender_defend_position += 3*(abs(i[0].row - defender_ai.row) + abs(i[0].col - defender_ai.col))
                    tech_turn +=1
                else:
                    defender_attack_position += -31
                    defender_attack_position += 3*(abs(i[0].row -attacker_ai.row) + abs(i[0].col - attacker_ai.col))
            elif i[1].type.name == "Program":
                defender_attack_position += -31
                defender_attack_position += 3*(abs(i[0].row -attacker_ai.row) + abs(i[0].col - attacker_ai.col))
            
        if player == 0: #the bigger the better
            return (defender_attack_position+defender_defend_position)-(attacker_attack_position+attacker_defend_position)
        if player == 1:
            return (attacker_attack_position+attacker_defend_position)-(defender_attack_position+defender_defend_position)

    '''
    The evaluate function 1 is designed based on the the health value of the units. 
    Except for ai, virus and Tech are considered to have higher value than other units
    '''
    def evaluate2(self, player : int) -> float:
        attacker_num = 0
        defender_num = 0
        for i in self.player_units(Player.Attacker):
            if i[1].type.name == "AI":
                attacker_num = attacker_num + i[1].health*100
            elif i[1].type.name == "Virus":
                attacker_num = attacker_num + i[1].health*9
            else:
                attacker_num = attacker_num + i[1].health*3
        for i in self.player_units(Player.Defender):
            if i[1].type.name == "AI":
                defender_num  = defender_num  +i[1].health*100
            elif i[1].type.name == "Tech":
                defender_num  = defender_num  +i[1].health*9
            else:
                defender_num  = defender_num  +i[1].health*3
        #attacker's value is 0, defender's value is 1
        if player == 0:
            return attacker_num-defender_num
        if player == 1:
            return defender_num-attacker_num


    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None

##############################################################################################################

def boolean_string(s):
    return s.lower() == 'true'

##############################################################################################################

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default="manual", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    parser.add_argument('--max_turns', type=int, help='maximum number of moves before end of game')
    parser.add_argument('--alpha_beta', type=boolean_string, default=False, help='true:ai uses alpha-beta; false: ai uses minimax')
    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.max_turns is not None:
        options.max_turns = args.max_turns
    if args.broker is not None:
        options.broker = args.broker
    if args.alpha_beta is not None:
        options.alpha_beta = args.alpha_beta

    
    playerOne = 'H' if game_type == GameType.AttackerVsComp or game_type == GameType.AttackerVsDefender else 'AI'
    playerTwo = 'H\n\n' if game_type == GameType.CompVsDefender or game_type == GameType.AttackerVsDefender else 'AI\n\n'

     # create a new game
    game = Game(options=options)
    # game.options.evaluation = 2

    
    global f 
    f = open(f'gameTrace-{str(args.alpha_beta).lower()}-{str(options.max_time)}-{str(options.max_turns)}.txt', 'w')
    f.write('Game Parameters:\n- game timeout (seconds): ' + str(options.max_time) +
            '\n- max turns: ' + str(options.max_turns) +
            '\n- Evaluation function used : e' + str(game.options.evaluation)+
            '\n- Player 1 : ' + playerOne +
            '\n- Player 2 : ' + playerTwo)

   
    

    f.write('Initial board configuration:\n\n' + Game.print_board(game) + '\n\n\n')

    # the main game loop
    while True:
        print()
        print(game)
        global winner
        winner = game.has_winner()
        if winner is not None:
            print(f"{winner.name} wins!")
            f.write(f'\n{winner.name} wins in {game.turns_played} turns!')
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn()
        else:
            player = game.next_player
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                f.close()
                exit(1)
        f.write('Turn #' + str(game.turns_played) + 
                '\nPlayer: ' + game.next_player.next().name +
                '\nMove: ' + str(game.last_move) + 
                '\n' + Game.print_board(game) + '\n\n')
    f.close()

##############################################################################################################

if __name__ == '__main__':
    main()
