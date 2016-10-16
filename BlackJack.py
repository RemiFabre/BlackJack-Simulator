# -*- coding: utf-8 -*-
import sys
from random import shuffle


#import codecs
#sys.stdout = codecs.getwriter("iso-8859-1")(sys.stdout, 'xmlcharrefreplace')
# Type this in the windows console : chcp 65001
#sigh : commented out because no lib and no internet available

#sigh tablefmt="" <-> tablefmt=""
import numpy as np
#sigh import scipy.stats as stats
#import pylab as pl
import matplotlib.pyplot as plt
import copy
from tabulate import tabulate
from importer.StrategyImporter import StrategyImporter
import logging

LOG_FILENAME = 'results.log'
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL

# create logger
logger = logging.getLogger("fileLogger")
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.FileHandler(LOG_FILENAME)
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)

logger.debug('Starting BlackJack.py...')

### Calculation related variables
GAMES = 10000
MAX_CARDS_ALLOWED = 6 # If the player is dealt 6 cards, then he can't draw again. This should significantly reduce the calculation times (and some BJ sites also have a similar rule for actual play)
MAX_CARDS_ALLOWED_DEALER = 8

RIDICULOUS_PROBA = 0.005/100.0 # 1 / 20 000
SMALL_NUMBER = 0.000001
NB_SPREADS = 0

### Rules definition

# A game is a number of shoes played (the last hand might be shuffled in between though)
NB_SHOES_PER_GAME = 1
SHOE_SIZE = 8
SHOE_PENETRATION = 0.55
BET_SPREAD = 20.0
DOUBLE_AFTER_SPLIT_ALLOWED = False
# CAN_HIT_ACES = False # Not implemented, you never can hit spllit aces anyways
# HITS_SOFT_17 # Not implemented, False by default
PEAKS_FOR_ACE = True
BJ_RATIO = 1.5

# Defines the authorized double range (can be reduced to 9, 10, 11 in some casinos)
MIN_DOUBLE=2
MAX_DOUBLE=20

### Game global variables

DECK_SIZE = 52.0
BLACKJACK = "BJ"
BUSTED = "BU"
NOT_APPLICABLE = "N/A"
CARDS_ORDER = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King"]
CARDS = {"Ace": 11, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10, "Jack": 10, "Queen": 10, "King": 10}
VALUE_TO_NAME = {11 : "Ace", 2 : "Two", 3 : "Three", 4 : "Four", 5 : "Five", 6 : "Six", 7 : "Seven", 8 : "Eight", 9 : "Nine", 10 : "Ten"}
y = {11 : "Ace", 2 : "Two", 3 : "Three", 4 : "Four", 5 : "Five", 6 : "Six", 7 : "Seven", 8 : "Eight", 9 : "Nine", 10 : "Ten"}
BASIC_OMEGA_II = {"Ace": 0, "Two": 1, "Three": 1, "Four": 2, "Five": 2, "Six": 2, "Seven": 1, "Eight": 0, "Nine": -1, "Ten": -2, "Jack": -2, "Queen": -2, "King": -2}
COUNT = {"Ace": SHOE_SIZE*4, "Two": SHOE_SIZE*4, "Three": SHOE_SIZE*4, "Four": SHOE_SIZE*4, "Five": SHOE_SIZE*4, "Six": SHOE_SIZE*4, "Seven": SHOE_SIZE*4, "Eight": SHOE_SIZE*4, "Nine": SHOE_SIZE*4, "Ten": SHOE_SIZE*4, "Jack": SHOE_SIZE*4, "Queen": SHOE_SIZE*4, "King": SHOE_SIZE*4}
nb_cards = DECK_SIZE*SHOE_SIZE

HARD_STRATEGY = {}
SOFT_STRATEGY = {}
PAIR_STRATEGY = {}


def is_number(x) :
    try:
        x += 1
        return True
    except TypeError:
        return False

class Card(object):
    """
    Represents a playing card with name and value.
    """
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return "%s" % self.name


class Shoe(object):
    """
    Represents the shoe, which consists of a number of card decks.
    """
    reshuffle = False

    def __init__(self, decks):
        self.count = 0
        self.count_history = []
        self.decks = decks
        self.cards = self.init_cards()
        self.init_count()

    def __repr__(self):
        s = ""
        for c in self.cards:
            s += "%s\n" % c
        return s

    def init_cards(self):
        """
        Initialize the shoe with shuffled playing cards and set count to zero.
        """
        self.count = 0
        self.count_history.append(self.count)

        cards = []
        for d in range(self.decks):
            for c in CARDS:
                for i in range(0, 4):
                    cards.append(Card(c, CARDS[c]))
        shuffle(cards)
        return cards

    def init_count(self):
        global COUNT, nb_cards
        nb_cards = DECK_SIZE*SHOE_SIZE
        for c in COUNT :
            COUNT[c] = 4*SHOE_SIZE

    def deal(self):
        """
        Returns:    The next card off the shoe. If the shoe penetration is reached,
                    the shoe gets reshuffled.
        """
        global COUNT, nb_cards
        if self.shoe_penetration() < SHOE_PENETRATION:
            self.reshuffle = True
        card = self.cards.pop()
        if (COUNT[card.name] <= 0) :
            print("Either a cheater or a bug !")
            sys.exit()
            if (nb_cards <= 0) :
                print("No more cards to deal, huge bug somewhere")
                sys.exit()
        COUNT[card.name] = COUNT[card.name] - 1
        nb_cards = nb_cards - 1
        self.do_count(card)
        return card

    def do_count(self, card):
        """
        Add the dealt card to current count.
        """
        self.count += BASIC_OMEGA_II[card.name]
        self.count_history.append(self.truecount())

    def truecount(self):
        """
        Returns: The current true count.
        """
        return self.count / (self.decks * self.shoe_penetration())

    def shoe_penetration(self):
        """
        Returns: Ratio of cards that are still in the shoe to all initial cards.
        """
        return len(self.cards) / (DECK_SIZE * self.decks)

class Hand(object):
    """
    Represents a hand, either from the dealer or from the player
    """
    _value = 0
    _aces = []
    _aces_soft = 0
    splithand = False
    surrender = False
    doubled = False

    def __init__(self, cards):
        self.cards = cards

    def __repr__(self):
        h = ""
        for c in self.cards:
            h += "%s " % c
        return h

    @property
    def value(self):
        """
        Returns: The current value of the hand (aces are either counted as 1 or 11).
        """
        self._value = 0
        for c in self.cards:
            self._value += c.value

        if self._value > 21 and self.aces_soft > 0:
            for ace in self.aces:
                if ace.value == 11:
                    self._value -= 10
                    ace.value = 1
                    if self._value <= 21:
                        break

        return self._value

    @property
    def aces(self):
        """
        Returns: The all aces in the current hand.
        """
        self._aces = []
        for c in self.cards:
            if c.name == "Ace":
                self._aces.append(c)
        return self._aces

    @property
    def aces_soft(self):
        """
        Returns: The number of aces valued as 11
        """
        self._aces_soft = 0
        for ace in self.aces:
            if ace.value == 11:
                self._aces_soft += 1
        return self._aces_soft

    def soft(self):
        """
        Determines whether the current hand is soft (soft means that it consists of aces valued at 11).
        """
        if self.aces_soft > 0:
            return True
        else:
            return False

    def splitable(self):
        """
        Determines if the current hand can be splitted.
        """
        if self.length() == 2 and self.cards[0].name == self.cards[1].name:
            return True
        else:
            return False

    def blackjack(self):
        """
        Check a hand for a blackjack. Note: 3x7 is NOT counted as a blackjack.
        """
        if not self.splithand and self.value == 21:
            if self.length() == 2:
                return True
            else:
                return False
        else:
            return False

    def busted(self):
        """
        Checks if the hand is busted.
        """
        if self.value > 21:
            return True
        else:
            return False

    def add_card(self, card):
        """
        Add a card to the current hand.
        """
        self.cards.append(card)

    def split(self):
        """
        Split the current hand.
        Returns: The new hand created from the split.
        """
        self.splithand = True
        c = self.cards.pop()
        new_hand = Hand([c])
        new_hand.splithand = True
        return new_hand

    def length(self):
        """
        Returns: The number of cards in the current hand.
        """
        return len(self.cards)


class Player(object):
    """
    Represent a player
    """
    def __init__(self, hand=None, dealer_hand=None):
        self.hands = [hand]
        self.dealer_hand = dealer_hand

    def set_hands(self, new_hand, new_dealer_hand):
        self.hands = [new_hand]
        self.dealer_hand = new_dealer_hand

    def play(self, shoe, ideal_play=False, dealer=None):
        for hand in self.hands:
            # print "Playing Hand: %s" % hand
            self.play_hand(hand, shoe, ideal_play = ideal_play, dealer = dealer)

    #@profile
    def play_hand(self, hand, shoe, ideal_play=False, dealer=None):
        if hand.length() < 2:
            if hand.cards[0].name == "Ace":
                hand.cards[0].value = 11
            self.hit(hand, shoe)

        print("********* Starting Player hand (in ideal calculation) : ", hand)
        while not hand.busted() and not hand.blackjack():
            if ideal_play == False :
                print("value = '", hand.value, "', name = '", self.dealer_hand.cards[0].name, "'")
                print("Line : ", HARD_STRATEGY[hand.value])
                if hand.soft():
                    flag = SOFT_STRATEGY[hand.value][self.dealer_hand.cards[0].name]
                elif hand.splitable():
                    flag = PAIR_STRATEGY[hand.value][self.dealer_hand.cards[0].name]
                else:
                    flag = HARD_STRATEGY[hand.value][self.dealer_hand.cards[0].name]
            else :
                # Finding out the ideal play
                if (dealer == None) :
                    print("Can't fond out the ideal play if you don't give me the dealer's up card buddy")
                    sys.exit()
                # Getting the dealer's stats from his card (has to be re-calculated after each card drawn by the player)
                dealer_value = dealer.hand.value
                print("dealer_value = ", dealer_value)
                dealer_stat_score = dealer.get_probabilities(dealer_value)
                print("Dealer's stats : ", dealer_stat_score)
                EVs = self.get_hand_EVs(hand, dealer_stat_score)
                print("Player hand (in ideal calculation) : ", hand)
                print ("Evs = ", EVs)
                best_call = self.get_ideal_option(EVs)
                flag = best_call[0]
                print("--->  Ideal call : ", best_call)

            if flag == 'D':
                if hand.length() == 2:
                    # print "Double Down"
                    hand.doubled = True
                    self.hit(hand, shoe)
                    break
                else:
                    flag = 'H'

            if flag == 'Sr':
                if hand.length() == 2:
                    # print "Surrender"
                    hand.surrender = True
                    break
                else:
                    flag = 'H'

            if flag == 'H':
                self.hit(hand, shoe)

            if flag == 'P':
                self.split(hand, shoe, ideal_play = ideal_play, dealer = dealer)

            if flag == 'S':
                break

    def hit(self, hand, shoe):
        c = shoe.deal()
        hand.add_card(c)
        # print "Hitted: %s" % c

    def split(self, hand, shoe, ideal_play=False, dealer=None):
        self.hands.append(hand.split())
        # print "Splitted %s" % hand
        #self.play_hand(hand, shoe)
        self.play_hand(hand, shoe, ideal_play = ideal_play, dealer = dealer)

    #TODO The dealer stat_score is assumed to be constant. This is not accurate since the card picked by the player affects the dealer's stats
    #This is sufficiently impactfull to make some noticeable changes in the optimal chart for single decked games
    #@profile
    def get_hand_EVs(self, hand, dealer_stat_score, forbid_split = False, forbid_double = False, no_bj = False):
        """
        Returns a map with the 4 EVs : stand_EV, hit_EV, double_EV, split_EV. The keys are the strings S, H, D and P.
        The best EV is the only one to be guaranteed to be calculated.
        If any option is impossible or if the EV is not known,
        the string NOT_APPLICABLE replaces the EV. This can be the case when stand is the best option and the hit
        EV wasn't fully calculated in order to save some calculation time.
        """
        new_count = copy.deepcopy(COUNT)
        new_nb_cards = nb_cards
        results_per_card = []
        ev_per_card = []
        start_value = 0
        nb_cards_in_hand = 0
        for v in hand.cards :
            #TODO use the hand.value method instead
            start_value = start_value + v.value
            nb_cards_in_hand = nb_cards_in_hand + 1

        if (start_value == 21 and nb_cards_in_hand == 2 and no_bj == False) :
            start_value = BLACKJACK
        # When the player is dealt its 2 cards, he has 4 options : stay, hit, double or split (in case of a pair).
        # Knowing the EV for the stay option is instantaneous. The current known score is compared to the dealers statistically estimated list of scores.
        # Knowing the EV for the double option requires to draw 1 card and then compare the repartition with the dealer's.
        # Knowing the EV for the pair option is equivalent to creating 2 hands and starting over,
        # for each hand the first card is known and the second one is purely statistical.
        #
        # Knowing the EV for the hit option is trickier. After drawing a card, each potential new value must be treated on its own to decide
        # either to stand or to hit. Each new hit creates a new list of potential values, each needing again the same research on stand vs hit.
        # The research ends when the only remaining options are stands. Only then can we go back recursively and calculate the actual EV of the first hit option !
        # A few rules :
        # - Must stand on 21, BLACKJACK and BUSTED
        # - Always hit if current score <= 11
        # - If after a hit, the optimistic EV is lower than the previous stand EV, then stand
        # - If the premature EV of a hit is greater than the stand EV, then hit (but we still need to keep investigating the tree if we want the actual EV)
        if hand.soft() :
            print("(Soft) start_value = ", start_value, ", hand : ", hand)
            score = Score(start_value, 1.0, 1.0, nb_cards_in_hand)
        else :
            print("(Hard) start_value = ", start_value, ", hand : ", hand)
            score = Score(start_value, 1.0, 0.0, nb_cards_in_hand)

        split_EV = NOT_APPLICABLE
        if (forbid_split == False and len(hand.cards) == 2 and hand.cards[0].name == hand.cards[1].name) :
            # We can split. We're going to call this very function with only the first current card and double the results.
            # TODO This is a big approximation since the second hand will be played with a different deck AND we're not considering
            # the possibilities of re-splits at all (usualy you can play up to 4 hands). Big TODO here, quite easy imo.
            print("Trying to split hand...")
            half_hand = Hand([hand.cards[0]])
            # The double after split (DAS) rule is equivalent to toggle the forbid_double flag here :
            if (hand.cards[0].name == "Ace") :
                # Can't hit split aces rule (this is equivalent to considering the double option and dividing its EV by 2)
                # TODO we're calculating more than what we need here, we only need the double EV.
                EVs = self.get_hand_EVs(half_hand, dealer_stat_score, forbid_split = True, forbid_double = False, no_bj = True)
                hit_only_once_ev = EVs["D"]/2
                print("hit_only_once_ev = ", hit_only_once_ev)
                EVs["D"] = NOT_APPLICABLE
                EVs["H"] = hit_only_once_ev
            else :
                if (DOUBLE_AFTER_SPLIT_ALLOWED) :
                    EVs = self.get_hand_EVs(half_hand, dealer_stat_score, forbid_split = True, forbid_double = False, no_bj = True)
                else :
                    EVs = self.get_hand_EVs(half_hand, dealer_stat_score, forbid_split = True, forbid_double = True, no_bj = True)
            split_EV = 2*self.get_ideal_option(EVs)[1]
##            print("actual split_EV = ", split_EV)

        double_EV = NOT_APPLICABLE
        if (forbid_double == False and score.value >= MIN_DOUBLE and score.value <= MAX_DOUBLE) :
            double_EV = score.double_EV(dealer_stat_score, new_count, new_nb_cards, no_bj = no_bj)

        stand_EV = score.EV(dealer_stat_score, BJratio=BJ_RATIO, debug=False, no_bj = no_bj)
        ideal_EV_results = score.ideal_EV(dealer_stat_score, new_count, new_nb_cards, no_bj = no_bj)

        print("stand_EV : ", stand_EV)
        print("ideal EV : ", ideal_EV_results)
        print("double_EV = ", double_EV)
        print("split_EV = ", split_EV)

        max_EV = ideal_EV_results[0]
        hit_EV = NOT_APPLICABLE
        if (max_EV > stand_EV) :
            hit_EV = max_EV

        result = {}
        result["S"] = stand_EV
        result["H"] = hit_EV
        result["D"] = double_EV
        result["P"] = split_EV
        return result

    def get_ideal_option(self, EVs) :
        """
        Return [Ideal_option, EV]. Ideal_option can be : S, H, D, P.
        """
        first = True
        best_option = "None?"
        max_EV = 0.0
        for o in EVs :
            if (EVs[o] != NOT_APPLICABLE and first) :
                first = False
                best_option = o
                max_EV = EVs[o]
            elif (EVs[o] != NOT_APPLICABLE) :
                if (max_EV < EVs[o]) :
                    best_option = o
                    max_EV = EVs[o]
        if (first) :
            print("No option seems to be possible in get_ideal_option ?")
            sys.exit()
        return [best_option, max_EV]


class Dealer(object):
    """
    Represent the dealer
    """
    def __init__(self, hand=None):
        self.hand = hand

    def set_hand(self, new_hand):
        self.hand = new_hand

    def play(self, shoe):
        while self.hand.value < 17:
            self.hit(shoe)

    def hit(self, shoe):
        c = shoe.deal()
        self.hand.add_card(c)
        # print "Dealer hitted: %s" %c

    ''' Returns a StatScore representing the probability that the final score of the dealer, with a maximum of NB_MAX_CARDS.
        [17, 18, 19, 20, 21, BJ, Busted] '''
    def get_probabilities(self, starting_value=None) :
        #print()
        #print("*** START")
        #print("COUNT = ", COUNT)
        #print("nb_cards = ", nb_cards)
        new_count = copy.deepcopy(COUNT)
        new_nb_cards = nb_cards
        if (starting_value == None) :
            # We'll assume the dealer has already a card in hand
            start_value = int(self.hand.value)
        else :
            # We're forcing a starting card :
            start_value = starting_value
            if (start_value == 10) :
                # A bit annoying : when simulating a 10 as the first card, we don't care if it's 10, J, Q or K. We'll just pick the card that
                # is the most present.
                actual_card = "Ten"
                max = COUNT[actual_card]
                if (max < COUNT["Jack"]) :
                    max = COUNT["Jack"]
                    actual_card = "Jack"
                if (max < COUNT["Queen"]) :
                    max = COUNT["Queen"]
                    actual_card = "Queen"
                if (max < COUNT["King"]) :
                    max = COUNT["King"]
                    actual_card = "King"
            else :
                actual_card = VALUE_TO_NAME[start_value]
            # Taking that card out of the deck
            if (new_count[actual_card] < 1) :
                #print("We're forcing a '", start_card, "' out of the deck but there is none left. You should've checked !")
                sys.exit()
            new_count[actual_card] = new_count[actual_card] - 1
            new_nb_cards = new_nb_cards - 1

        #print ("start_value = ", start_value)
        # The dealer will stop if his hand's value is any of stop_scores
        stat_score = StatScore(start_value, stop_scores=[17, 18, 19, 20, 21, BLACKJACK, BUSTED])
        #print ("Stat_score (1 card) = ", stat_score)
        #print()

        for i in range(MAX_CARDS_ALLOWED_DEALER-1) :
            #print("Picking up card number ", i+1," from the deck ...")
            stat_card = StatCard(new_count, new_nb_cards)
            new_count, new_nb_cards = stat_card.get_new_count()
            #print ("Stat_card = ", stat_card)
            # "Nine" -> 9
            card_values = stat_card.get_card_values()
            stat_score.draw_card(card_values)
            #print ("Stat_score (", i+2, " cards) = ", stat_score)
            #print("(end)Remaining proba = ", stat_score.remaining_proba)
            sum = 0
            for v in stat_score.values :
                sum = sum + stat_score.values[v]
            #print("Sum of probas = ", sum)
            #print()
            if (stat_score.remaining_proba < RIDICULOUS_PROBA) :
                # We're saving some calculation time
                break

        #print("** STOP")
        #print()

        return stat_score

class StatCard(object) :
    """
    Represents the probability of a card among ["Ace", "Two", ..., "King"].
    """
    # Creates a StatCard from the (ideal) count of the remaining cards.
    def __init__(self, count, nb_cards, fake=False, simple_value=2) :
        self.new_count = copy.deepcopy(count)
        #TODO Check this -1 !
        self.new_nb_cards = nb_cards -1
        self.values = {}
        if (not(fake)) :
            for c in count :
                self.values[c] = count[c]/float(nb_cards)
                # After picking a card, the likelihood of each value changes. new_count is updated to take that into account by
                # subtracting "portions" of cards, proportionally to the card's likeliness. The sum of the portions should be 1.0
                # TODO this is actually an approximation. The exact method would be to save a whole number count per card drawn.
                self.new_count[c] = self.new_count[c] - self.values[c]
        else :
            for c in count :
                if (CARDS[c] == simple_value and simple_value != 10) :
                    self.values[c] = 1.0
                else :
                    self.values[c] = 0.0
            # Otherwise all the 10 values (T, J, Q, K) would get a 1.0 proba...
            if (simple_value == 10) :
                    self.values["Ten"] = 1.0

    def __repr__(self):
        s = "\n"
        data = []

        header = []
        probas = []
        for v in CARDS_ORDER :
            header.append(v)
            probas.append("{0:.2f}".format(100*self.values[v]))
        data = [probas]
        s = s + tabulate(data, headers=header, tablefmt="")
        return s

    def ugly_print(self):
        s = ""
        for v in self.values :
            s = s + "[" + v + ": " + "{0:.1f}".format(100*self.values[v]) + "], "
        return s

    def get_new_count(self) :
        return self.new_count, self.new_nb_cards

    """
    From ({"Two":0.02, "Three":0.02, ...}) to ({2:0.02, 3:0.02, ...})
    All heads are 10, ace value is 11.
    """
    def get_card_values(self) :
        result = {10:0.0}
        for c in self.values :
            if (CARDS[c] == 10) :
                # Several cards are worth 10
                result[10] = result[10] + self.values[c]
            else :
                result[CARDS[c]] = self.values[c]
        return result


class Score(object) :
    """
    Represents a single score among [2, 3, ..., 21, BlackJack, Busted].
    """
    def __init__(self, value, proba, soft_ace_proba, nb_cards) :
        self.value = value
        self.proba = proba
        self.soft_ace_proba = soft_ace_proba
        self.nb_cards = nb_cards

    def __repr__(self):
        s = "\n["
        s += str(self.value) + ", " + str(self.proba) + ", " + str(self.soft_ace_proba) + "]"
        return s

    def get_stat_score(self) :
        stat_score = StatScore(self.value)
        if (self.nb_cards > 1 and stat_score.nb_cards_in_hand < 2) :
            stat_score.nb_cards_in_hand = 2
        # Clearing the soft_ace_probas and setting it again if this is a soft_score
        for i in range(21) :
            stat_score.soft_ace_proba[i+1] = 0.0
        if (is_number(self.value)) :
            stat_score.soft_ace_proba[self.value] = self.soft_ace_proba
        stat_score.total_proba = self.proba
        
        return stat_score

    def EV(self, o_stat_value, BJratio=BJ_RATIO, debug=False, no_bj=False) :
        # o_stat_value = opponent's stat_value
        winrate = 0.0
        tierate = 0.0
        loserate = 0.0
        BJwinrate = 0.0
        bustrate = 0.0
        score = self.value
        p = self.proba
        sum_of_proba = 0
        
        if (no_bj and (score == BLACKJACK)) :
            print("No bj ;''''(")
            score = 21

        for o_score in o_stat_value.values :
            o_p = o_stat_value.values[o_score]
            sum_of_proba = sum_of_proba + o_p*p
            if (score == BUSTED) :
                # We busted, we lost no matter what
                loserate = loserate + p*o_p
                bustrate = bustrate + p*o_p
            elif (score == BLACKJACK and o_score != BLACKJACK) :
                BJwinrate = BJwinrate + p*o_p
            elif (o_score == BUSTED) :
                winrate = winrate + p*o_p
            elif (score != BLACKJACK and o_score == BLACKJACK) :
                loserate = loserate + p*o_p
            elif (score == o_score) :
                tierate = tierate + p*o_p
            elif (int(score) > int(o_score)) :
                winrate = winrate + p*o_p
            else :
                loserate = loserate + p*o_p

        ev = winrate - loserate + BJratio*BJwinrate

        if (debug) :
            print("Calculated EV.\nself : ", self, "\no_stat_value", o_stat_value, "\nEV = ", ev, "\nsum_of_proba = ", sum_of_proba)
            print("winrate = ", winrate)
            print("tierate = ", tierate)
            print("loserate = ", loserate)
            print("bustrate = ", bustrate)
        
        return ev

    # Returns the EV of the optimal play. The sum of probas and the number of calls are returned too,
    # as a verification measure :
    # output = [EV, sum of probas that should be 1, number of calls]
    def ideal_EV(self, dealer_stat_score, new_count, new_nb_cards, no_bj=False) :
        if (no_bj) :
            EV_without_hit = self.EV(dealer_stat_score, BJ_RATIO, False, no_bj=no_bj)
        else :
            EV_without_hit = self.EV(dealer_stat_score)

        if self.value == 21 or self.value == BUSTED or self.value == BLACKJACK or self.nb_cards >= MAX_CARDS_ALLOWED :
            # We're stopping here no matter what
            #print("Score : ", self.value, ". Returning : ", [EV_without_hit, self.proba, 1])
            return [EV_without_hit, self.proba, 1]
        else :
            # Turning into a StatScore
            stat_score = self.get_stat_score()
            # Hitting a statistical card
            stat_card = StatCard(new_count, new_nb_cards)
            new_count, new_nb_cards = stat_card.get_new_count()
            card_values = stat_card.get_card_values()
            stat_score.draw_card(card_values)

            # Checking if hitting a card is an obvious disaster :
            rates = stat_score.winrate_vs_statvalue(dealer_stat_score)
            # Must multiply by self.proba here since StatScore doesn't take it into account (sum of probas == 1 convention)
            optimistic_ev = stat_score.ev_limit_by_bust(rates)*self.proba
            if (optimistic_ev <= EV_without_hit) :
                # No point in calculating the actual hit ev, it'll be below the stand ev
                #print("no point in going further, optimistic ev = ", optimistic_ev)
                #print("Score (No Point) : ", self.value, ". Returning : ", [EV_without_hit, self.proba, 1])
                return [EV_without_hit, self.proba, 1]

            # Checks each individual value's EV
            EV_sum = 0.0
            proba_sum = 0.0
            nb_calls = 1
            for v in stat_score.values :
                if stat_score.values[v] == 0.0 :
                    continue
                # Creating a Score that will be investigated on its own
                new_score = Score(v, self.proba*stat_score.values[v], stat_score.soft_ace_proba[v], self.nb_cards + 1)
                # If we stand on the current value, the EV is known :
                EV_stand = new_score.EV(dealer_stat_score)
                results = new_score.ideal_EV(dealer_stat_score, new_count, new_nb_cards, no_bj = no_bj)
                # No need to multiply by new_score.proba since all the EVs calculated are already dependy on the scores proba
                EV_sum = EV_sum + max(EV_stand, results[0])
                proba_sum = proba_sum + results[1]
                nb_calls = nb_calls + results[2]
                if (abs(new_score.proba - results[1]) > SMALL_NUMBER) :
                    print("Nah-ah. new_score.proba = ", new_score.proba, ", results[1] = ", results[1])
                    sys.exit()
            #print("Score (after sum) : ", self.value, ". Returning : ", [max(EV_without_hit, EV_sum), proba_sum, nb_calls])
            #print("EV_sum = ", EV_sum, ", EV_without_hit = ", EV_without_hit)
            return [max(EV_without_hit, EV_sum), proba_sum, nb_calls]

    # Returns the EV expected when doubling down (bet is x2 but you must draw 1 card and 1 card only)
    def double_EV(self, dealer_stat_score, new_count, new_nb_cards, no_bj = False) :
        # Turning into a StatScore
        stat_score = self.get_stat_score()

        # Hitting a statistical card
        stat_card = StatCard(new_count, new_nb_cards)
        new_count, new_nb_cards = stat_card.get_new_count()
        card_values = stat_card.get_card_values()
        stat_score.draw_card(card_values)

        rates = stat_score.winrate_vs_statvalue(dealer_stat_score, no_bj = no_bj)
        #print("DOUBLE STAT SCORE : ", stat_score)

        return 2*stat_score.ev_from_winrate(rates)

    @staticmethod
    def get_maps_of_scores(stat_card1, stat_card2) :
        """
        Returns 3 maps with each possible score and its probability : hard scores, soft scores and pairs.
        """
        map_of_hard_scores = {}
        map_of_soft_scores = {}
        map_of_pair_scores = {}

        for i in range(16) :
            #from 5 to 20 (cos 4 can only be a pair. 20 doesn't have to be a pair, e.g JQ)
            value = i+5
            score = Score(value, 0.0, 0.0, 2)
            map_of_hard_scores[value] = score

        for i in range(8) :
            #from 13 to 20 plus BLACKJACK
            value = i+13
            score = Score(value, 0.0, 100.0, 2)
            map_of_soft_scores[value] = score
        score = Score(BLACKJACK, 0.0, 100.0, 2)
        map_of_soft_scores[BLACKJACK] = score

        for i in range(10) :
            #from 2 to 11 (saving only the first value)
            value = i+2
            if (value == 11) :
                score = Score(value, 0.0, 100.0, 2)
            else :
                score = Score(value, 0.0, 0.0, 2)
            map_of_pair_scores[value] = score

        sum = 0.0
        for c1 in stat_card1.values :
            p1 = stat_card1.values[c1]
            for c2 in stat_card2.values :
                p2 = stat_card2.values[c2]
                # Going from nine to 9
                v1 = CARDS[c1]
                v2 = CARDS[c2]
                value = v1 + v2
                proba = p1*p2
                sum = sum + proba
                if (value == 21) :
                    # Only one way to get 21 with 2 cards
                    value = BLACKJACK
                if (c1 == c2) :
                    # Its a pair
                    map_of_pair_scores[v1].proba = map_of_pair_scores[v1].proba + proba
                elif (v1 == 11 or v2 == 11) :
                    # Its a soft score
                    map_of_soft_scores[value].proba = map_of_soft_scores[value].proba + proba
                else :
                    map_of_hard_scores[value].proba = map_of_hard_scores[value].proba + proba

        return map_of_hard_scores, map_of_soft_scores, map_of_pair_scores

class StatScore(object) :
    """
    Represents the probability of a score being any value among [2, 3, ..., 21, BlackJack, Busted].
    """
    def __init__(self, start_value, stop_scores=[21, BLACKJACK, BUSTED]):
        self.start_value = start_value
        self.values = {}
        self.nb_cards_in_hand = 1
        self.stop_scores = stop_scores
        # In order to simplify stuff, the sum of all the scores probas has to be 1. Yet sometimes the whole StatScore has its own proba,
        # this is where we save that value (not used inside this class a priori though)
        self.total_proba = 1.0
        self.remaining_proba = 1.0
        # soft_ace_proba[i] is the probability that the score i is made with at least 1 soft ace.
        # Blackjack is always 100%) and Busted is always 0%.
        self.soft_ace_proba = {}
        for i in range(21) :
            self.soft_ace_proba[i+1] = 0.0
        self.soft_ace_proba[BLACKJACK] = 1.0
        self.soft_ace_proba[BUSTED] = 0.0
        if (start_value == 11) :
            # The start value is an ace
            self.soft_ace_proba[11] = 1.0
        """
        if (isinstance(start_value, dict)) :
            if (len(start_value) != 22) :
                print("A StatCard has always 22 values, wrong initializer")
                sys.exit()
            # We're already dealing with a dictionary
            self.values = start_value
        """
        # Initialization
        for i in range(21) :
            self.values[i+1] = 0.0
        self.values[BLACKJACK] = 0.0
        self.values[BUSTED] = 0.0

        # Setting to 100% the starting score
        if (start_value in self.stop_scores) :
            # No point in calculating anything, the dealer won't draw another card
            self.remaining_proba = 0.0
        if (start_value > 21) :
            start_value = BUSTED
        if (isinstance(start_value, int)) :
            self.values[start_value] = 1.0
        elif (start_value == BLACKJACK) :
            self.values[BLACKJACK] = 1.0
        elif (start_value == BUSTED) :
            self.values[BUSTED] = 1.0
        else :
            print("Wrong initializer in StatScore : '", start_value, "'")
            sys.exit()

    def __repr__(self):
        s = "\n"
        data = []

        header = []
        probas = []
        soft_ace_probas = []
        for v in self.values :
            header.append(v)
            probas.append("{0:.2f}".format(100*self.values[v]))
            soft_ace_probas.append("{0:.2f}".format(100*self.soft_ace_proba[v]))
        data = [probas, soft_ace_probas]
        s = s + tabulate(data, headers=header, tablefmt="")
        return s

    def ugly_print(self) :
        s = ""
        for v in self.values :
            s = s + "[" + str(v) + ": " + "{0:.1f}".format(100*self.values[v]) + "], "
        s = s + "\nsoft_ace_probas :"
        for v in self.soft_ace_proba :
            s = s + "[" + str(v) + ": " + "{0:.1f}".format(100*self.soft_ace_proba[v]) + "], "
        return s

    """
    Increases the odds of each score based on the chances of getting each card.
    If a score is in the stop_scores list, then no card can be added on it (that's why there is the remaining_proba mechanic).
    remaining_proba : quantifies the fact that the player/dealer won't ask for another card if a stop_score is already reached.

    To sum it up, if our strategy is to stop drawing cards if our score is on self.stop_scores, and we call draw_card until the
    self.remaining_proba is 0, then self.values will give the probability of each score.
    """
    #TODO re-read every formula, this is very error prone. Then double check with detailed simulation results
    def draw_card(self, card_values) :
        self.nb_cards_in_hand = self.nb_cards_in_hand + 1
        old_values = copy.deepcopy(self.values)
        old_soft_aces = copy.deepcopy(self.soft_ace_proba)
        sum_of_non_stop_scores = 0.0
        for score in self.values :
            if ((score in self.stop_scores) == False) :
                sum_of_non_stop_scores = sum_of_non_stop_scores + self.values[score]
                # Non stop_scores get their proba reset (since we're drawing a card and there is no "0" card)
                self.values[score] = 0.0
                self.soft_ace_proba[score] = 0.0
        if (sum_of_non_stop_scores != 0) :
            buff_ratio = 1.0/sum_of_non_stop_scores
            if (abs(sum_of_non_stop_scores - self.remaining_proba) > RIDICULOUS_PROBA) :
                print("sum_of_non_stop_scores should be equal to self.remaining_proba, unless we're doing some fancy stuff (that will probably be wrong :D)")

            for score in old_values :
                if (score in self.stop_scores) :
                    continue
                # We're considering the case where our current score is not a stop_score. Therefore, the sum of the possible non-stop_scores
                # probas must be 1. We're "buffing" their probas to achieve it.
                old_values[score] = old_values[score]*buff_ratio

        for score in self.values :
            if (old_values[score] == 0.0) :
                continue
            if (score in self.stop_scores) :
                # Can't draw a card on a stop_score
                continue
            for v in card_values :
                # v is the card value (2, 3, ..., 10 or 11) stat_card.values[v] is its proba
                new_value = v + score
                # Handling the case where the current card is an ace
                if (v == 11) :
                    # The new card is an ace
                    if (new_value > 21) :
                        # The ace is worth 1, no questions asked.
                        new_value = new_value - 10
                    else :
                        # The ace is worth 11, but the new_value's soft_ace_proba increases (100% of the population of new_value created with an 11-ace
                        # is by definition a soft_ace hand)
                        self.soft_ace_proba[new_value] = self.soft_ace_proba[new_value] + (card_values[v]*old_values[score]*1.0)*self.remaining_proba

                if (new_value > 21) :
                    # There is a chance that we still have a soft ace in our hand, reducing the proba of busting
                    # and increasing the proba of reaching new_value - 10.
                    soft_ace_proba = old_soft_aces[score]
                    new_proba_busted = (card_values[v]*old_values[score])*self.remaining_proba*(1-soft_ace_proba)
                    new_proba_not_busted = (card_values[v]*old_values[score])*self.remaining_proba*(soft_ace_proba)

                    # Handling the Busted population
                    self.values[BUSTED] = new_proba_busted + self.values[BUSTED]

                    # Handling the new_value - 10 population
                    new_value = new_value - 10
                    self.values[new_value] = new_proba_not_busted + self.values[new_value]
                    # Important note : we turned a soft-11 ace into a hard-1 one. This increased the odds of reaching new_value-10, but it should also
                    # lower the odds of having a soft-11 ace on new_value-10 (the small portion of hand population that we added has already a hard ace).
                    # The way this is handled is to assume that 100% of the new_value-10 population that we added by not busting has 0% chance of having another
                    # soft ace in it. Actually, this is exact since there is no hand that can have 2 soft aces (11+11 = busted)
                else :
                    # Updating the proba of having a soft ace only because of the previous cards
                    self.soft_ace_proba[new_value] = self.soft_ace_proba[new_value] + (card_values[v]*old_values[score]*old_soft_aces[score])*self.remaining_proba
                    # Handling the BJ case
                    if (new_value == 21 and self.nb_cards_in_hand == 2) :
                        new_value = BLACKJACK

                    # Handling the "normal" case
                    new_proba = (card_values[v]*old_values[score])*self.remaining_proba
                    self.values[new_value] = new_proba + self.values[new_value]

        # Ending the soft ace calculation. We need to wait until all the odds are calculated to do this ratio. Think of it like a ratio between a special
        # population (the soft ace hands) and the total population
        # Also updating the remaining proba. If it's 0, the player will never draw another card
        sum = 0.0
        for score in self.values :
            if (score in self.stop_scores) :
                # Can't draw a card on a stop_score
                continue
            if (self.values[score] == 0.0) :
                self.soft_ace_proba[score] = 0.0
                continue
            self.soft_ace_proba[score] = self.soft_ace_proba[score]/float(self.values[score])
            sum = sum + self.values[score]

        self.remaining_proba = sum

    # Returns [winrate, tierate, loserate, BJwinrate, bustrate]. The sum of the first 4 values should be 1.
    # The current statvalue loses if it busts, therefore this function should be used from
    # the player's statvalue and not from the Dealer's.
    #TODO this function is 80% a duplicate of .EV( ...
    def winrate_vs_statvalue(self, o_stat_value, no_bj = False) :
        # o_stat_value = opponent's stat_value
        winrate = 0.0
        tierate = 0.0
        loserate = 0.0
        BJwinrate = 0.0
        bustrate = 0.0
        for score in self.values :
            p = self.values[score]
            if (no_bj and (score == BLACKJACK)) :
                score = 21
            for o_score in o_stat_value.values :
                o_p = o_stat_value.values[o_score]
                if (score == BUSTED) :
                    # We busted, we lost no matter what
                    loserate = loserate + p*o_p
                    bustrate = bustrate + p*o_p
                elif (score == BLACKJACK and o_score != BLACKJACK) :
                    BJwinrate = BJwinrate + p*o_p
                elif (o_score == BUSTED) :
                    winrate = winrate + p*o_p
                elif (score != BLACKJACK and o_score == BLACKJACK) :
                    loserate = loserate + p*o_p
                elif (score == o_score) :
                    tierate = tierate + p*o_p
                elif (int(score) > int(o_score)) :
                    winrate = winrate + p*o_p
                else :
                    loserate = loserate + p*o_p
        # By opposition to a Score, a StatScore sum of probas must be 1. This is a convention that mostly comes from the fact that the code is working as is
        if (abs(winrate + loserate + tierate + BJwinrate - 1.0) > RIDICULOUS_PROBA) :
            print ("OH ! The sum of scores in winrate_vs_statvalue ain't no doing no self.total_proba (yup, I suddently turned black). o_stat_value : ", o_stat_value, ", self_stat_value : ", self)
            sys.exit()
        
        return [winrate, tierate, loserate, BJwinrate, bustrate]

    def ev_from_winrate(self, rates, BJratio=BJ_RATIO) :
        winrate = rates[0]
        tierate = rates[1]
        loserate = rates[2]
        BJwinrate = rates[3]

        ev = winrate - loserate + BJratio*BJwinrate
        return ev

    # Optimistic EV. Only considering the bust and BJ ratios, returns the best EV you can hope for
    def ev_limit_by_bust(self, rates, BJratio=BJ_RATIO) :
        BJwinrate = rates[3]
        bustrate = rates[4]
        fake_winrate = 1.0 - (bustrate + BJwinrate)

        fake_ev = fake_winrate - bustrate + BJratio*BJwinrate

        return fake_ev

class StatChart(object) :
    """
    Chart Representing the probability of a score among [2, 3, ..., 21, BlackJack, Busted] (cols) with any starting card (rows)
    """
    def __init__(self, card_values):
        self.map_of_stat_scores = {}
        self.card_values = card_values

    def __repr__(self):
        s = "\n"
        data = []

        header = ["Start "]
        probas = []
        # Reading the col names from any of the stat_scores
        for stat in self.map_of_stat_scores :
            for v in self.map_of_stat_scores[stat].values :
                header.append(v)
            break
        for i in range(10) :
            start_value = i + 2
            # The first col is the value of the first card and its proba
            probas.append(str(start_value) + " (" + "{0:.1f}".format(100*self.card_values[start_value])  + ")")
            for v in self.map_of_stat_scores[start_value].values :
                probas.append("{0:.2f}".format(100*self.map_of_stat_scores[start_value].values[v]))
            data.append(probas)
            probas = []

        s = s + tabulate(data, headers=header, tablefmt="")
        return s

    def add_to_map(self, key, stat_score) :
        self.map_of_stat_scores[key] = stat_score


class StrategyLine(object) :
    """
    Array representing the ideal strategy for 1 (player) Score against any dealer's up card (cols)
    """
    def __init__(self, player_score):
        self.player_score = player_score
        self.strategy = {}

    #Expects strat = [Ideal_option, EV]
    def append(self, dealer_value, strat) :
        self.strategy[dealer_value] = strat

    def __repr__(self):
        s = "\n"
        data = []

        header = ["Player\Dealer "]
        EVs = []
        # Creating the header from the dealer's stats
        for d in self.strategy :
            header.append(str(d))

        # The first col is the value of player's score
        EVs.append(str(self.player_score.value))
        for d in self.strategy :
            EVs.append(self.strategy[d][0] + " (" + "{0:.1f}".format(100*self.strategy[d][1])  + ")")
        data.append(EVs)

        s = s + tabulate(data, headers=header, tablefmt="")
        return s

class StrategyChart(object) :
    """
    Chart Representing the ideal strategy for any score (rows) against any dealer's up card (cols)
    """
    def __init__(self, dealer_card_values):
        self.map_of_strategy_lines = {}
        self.dealer_card_values = dealer_card_values
        
        print("dealer_card_values = ", dealer_card_values)
        for d in self.dealer_card_values :
            print(str(d) + " (" + "{0:.1f}".format(100*self.dealer_card_values[d])  + ")")

    def __repr__(self):
        s = "\n"
        data = []

        header = ["Player\Dealer "]
        EVs = []
        # Creating the header from the dealer's stats
        for d in self.dealer_card_values :
            header.append(str(d) + " (" + "{0:.1f}".format(100*self.dealer_card_values[d])  + ")")

        for p in self.map_of_strategy_lines :
            # The first col is the value of player's score and its proba
            EVs.append(str(self.map_of_strategy_lines[p].player_score.value) + " (" + "{0:.1f}".format(100*self.map_of_strategy_lines[p].player_score.proba)  + ")")
            for dealer_value in self.map_of_strategy_lines[p].strategy :
                EVs.append(self.map_of_strategy_lines[p].strategy[dealer_value][0] + " (" + "{0:.1f}".format(100*self.map_of_strategy_lines[p].strategy[dealer_value][1])  + ")")
            data.append(EVs)
            EVs = []

        s = s + tabulate(data, headers=header, tablefmt="")
        return s

    def add_to_map(self, score, strategy_line) :
        self.map_of_strategy_lines[score] = strategy_line

    def get_total_EV(self) :
        sum_of_probas = 0.0
        total_EV = 0.0
        for p in self.map_of_strategy_lines :
            for dealer_value in self.map_of_strategy_lines[p].strategy :
                #We're actually looping through every dealer value (but the StrategyLine obect doesn't know the proba of each dealer value)
                proba = self.dealer_card_values[dealer_value]*self.map_of_strategy_lines[p].player_score.proba
                EV = proba*self.map_of_strategy_lines[p].strategy[dealer_value][1]
                sum_of_probas = sum_of_probas + proba
                total_EV = total_EV + EV
        return total_EV, sum_of_probas

class Game(object):
    """
    A sequence of Blackjack Rounds that keeps track of total money won or lost
    """
    def __init__(self):
        self.shoe = Shoe(SHOE_SIZE)
        self.money = 0.0
        self.bet = 0.0
        self.stake = 1.0
        self.player = Player()
        self.dealer = Dealer()

    def get_hand_winnings(self, hand):
        win = 0.0
        bet = self.stake
        if not hand.surrender:
            if hand.busted():
                status = "LOST"
            else:
                if hand.blackjack():
                    if self.dealer.hand.blackjack():
                        status = "PUSH"
                    else:
                        status = "WON 3:2"
                elif self.dealer.hand.busted():
                    status = "WON"
                elif self.dealer.hand.value < hand.value:
                    status = "WON"
                elif self.dealer.hand.value > hand.value:
                    status = "LOST"
                elif self.dealer.hand.value == hand.value:
                    if self.dealer.hand.blackjack():
                        status = "LOST"  # player's 21 vs dealers blackjack
                    else:
                        status = "PUSH"
        else:
            status = "SURRENDER"

        if status == "LOST":
            win += -1
        elif status == "WON":
            win += 1
        elif status == "WON 3:2":
            win += BJ_RATIO
        elif status == "SURRENDER":
            win += -0.5
        if hand.doubled:
            win *= 2
            bet *= 2

        win *= self.stake

        return win, bet

    def calculate_strategy_chart_hard(self, map_of_hard_scores, dealer_card_values, stat_chart) : 
        strategy_chart_hard = StrategyChart(dealer_card_values)
        for s in map_of_hard_scores :
            # Checking the best call and EV when the player has the score s against the dealer's value (up card)
            player_value = map_of_hard_scores[s].value
            strategy_line = StrategyLine(map_of_hard_scores[s])
            # Hand made hands. TODO do better than this
            if (player_value < 13) :
                card1 = Card("Two", 2)
                card2_value = player_value - 2
                card2 = Card(VALUE_TO_NAME[card2_value], card2_value)
            else :
                card1 = Card("Ten", 10)
                card2_value = player_value - 10
                card2 = Card(VALUE_TO_NAME[card2_value], card2_value)

            player_hand = Hand([card1, card2])
            for i in range(10) :
                value = i + 2
                print("Player : ", player_hand, ", dealer = ", value)
                # That dealer's stats for value are :
                dealer_stat_score = stat_chart.map_of_stat_scores[value]
                EVs = self.player.get_hand_EVs(player_hand, dealer_stat_score)
                print ("Evs = ", EVs)
                best_call = self.player.get_ideal_option(EVs)
                print ("Best call : ", best_call)
                strategy_line.append(value, best_call)
            # Adding the strategy_line into the strategy chart
            print("strategy_line = ", strategy_line)

            strategy_chart_hard.add_to_map(s, strategy_line)
        return strategy_chart_hard

    def calculate_strategy_chart_soft(self, map_of_soft_scores, dealer_card_values, stat_chart) : 
        strategy_chart_soft = StrategyChart(dealer_card_values)
        for s in map_of_soft_scores :
            # Checking the best call and EV when the player has the score s against the dealer's value (up card)
            player_value = map_of_soft_scores[s].value
            strategy_line = StrategyLine(map_of_soft_scores[s])
            # Hand made hands.
            card1 = Card("Ace", 11)
            if (player_value == BLACKJACK) :
                card2 = Card("Ten", 10)
            else :
                card2_value = player_value - 11
                card2 = Card(VALUE_TO_NAME[card2_value], card2_value)

            player_hand = Hand([card1, card2])
            for i in range(10) :
                value = i + 2
                print("Player : ", player_hand, ", dealer = ", value)
                # That dealer's stats for value are :
                dealer_stat_score = stat_chart.map_of_stat_scores[value]
                EVs = self.player.get_hand_EVs(player_hand, dealer_stat_score)
                print ("Evs = ", EVs)
                best_call = self.player.get_ideal_option(EVs)
                print ("Best call : ", best_call)
                strategy_line.append(value, best_call)
            # Adding the strategy_line into the strategy chart
            print("strategy_line = ", strategy_line)

            strategy_chart_soft.add_to_map(s, strategy_line)
        return strategy_chart_soft
        
    def calculate_strategy_chart_pair(self, map_of_pair_scores, dealer_card_values, stat_chart) : 
        strategy_chart_pair = StrategyChart(dealer_card_values)
        for s in map_of_pair_scores :
            # Checking the best call and EV when the player has the score s against the dealer's value (up card)
            player_value = map_of_pair_scores[s].value
            strategy_line = StrategyLine(map_of_pair_scores[s])
            # Hand made hands.
            card_value = player_value
            card1 = Card(VALUE_TO_NAME[card_value], card_value)
            if (player_value == 11) :
                card2 = Card(VALUE_TO_NAME[card_value], 1)
            else :
                card2 = Card(VALUE_TO_NAME[card_value], card_value)
            
            player_hand = Hand([card1, card2])
            for i in range(10) :
                value = i + 2
                print("Player : ", player_hand, ", dealer = ", value)
                # That dealer's stats for value are :
                dealer_stat_score = stat_chart.map_of_stat_scores[value]
                EVs = self.player.get_hand_EVs(player_hand, dealer_stat_score)
                print ("Evs = ", EVs)
                best_call = self.player.get_ideal_option(EVs)
                print ("Best call : ", best_call)
                strategy_line.append(value, best_call)
            # Adding the strategy_line into the strategy chart
            print("strategy_line = ", strategy_line)

            strategy_chart_pair.add_to_map(s, strategy_line)
        return strategy_chart_pair

    # Returns true if a reshuffle took place during the round
    def play_round(self):
        global NB_SPREADS
        if self.shoe.truecount() > 5: # TODO do better than this
            self.stake = BET_SPREAD
            NB_SPREADS = NB_SPREADS + 1
        else:
            self.stake = 1.0

        # Checking out the dealers stats before the cards are dealt :
        stat_card = StatCard(COUNT, nb_cards)
        card_values = stat_card.get_card_values()
        stat_chart = StatChart(card_values)

        for i in range(10) :
            value = i + 2
            dealer_stat_score = self.dealer.get_probabilities(value)
            stat_chart.add_to_map(value, dealer_stat_score)
        print("StatChart for the Dealer (before drawing any card):", stat_chart)

        #TEMP TODO Attention ! xxx
        ##card_value = 11
        ##player_value = 11
        ##card1 = Card(VALUE_TO_NAME[card_value], card_value)
        ##if (player_value == 11) :
        ##    card2 = Card(VALUE_TO_NAME[card_value], 1)
        ##else :
        ##    card2 = Card(VALUE_TO_NAME[card_value], card_value)
        ##    
        ##player_hand = Hand([card1, card2])
        ##value = 11
        ##print("Player : ", player_hand, ", dealer = ", value)
        ### That dealer's stats for value are :
        ##dealer_stat_score = stat_chart.map_of_stat_scores[value]
        ##EVs = self.player.get_hand_EVs(player_hand, dealer_stat_score)
        ##print ("Evs = ", EVs)
        ##best_call = self.player.get_ideal_option(EVs)
        ##print ("Best call : ", best_call)
        ##input("Temp")
        # End of TEMP TODO Attention !
        
        
        # Creating a StrategyChart.
        # First of, what are the odds of getting any value with the first 2 cards?
        new_count = copy.deepcopy(COUNT)
        new_nb_cards = nb_cards
        stat_card1 = StatCard(new_count, new_nb_cards)
        #card_values1 = stat_card1.get_card_values()
        new_count, new_nb_cards = stat_card.get_new_count()
        stat_card2 = StatCard(new_count, new_nb_cards)
        #card_values2 = stat_card2.get_card_values()
        map_of_hard_scores, map_of_soft_scores, map_of_pair_scores = Score.get_maps_of_scores(stat_card1, stat_card2)
        
        '''
        strategy_chart_hard = self.calculate_strategy_chart_hard(map_of_hard_scores, card_values, stat_chart)
        print("Strategy chart hard : ", strategy_chart_hard)
        total_hard_EV, sum_of_probas_hard = strategy_chart_hard.get_total_EV()
        print("Total hard EV : {}, sum of probas : {}".format("{0:.2f}".format(100*total_hard_EV), "{0:.2f}".format(100*sum_of_probas_hard)))
        input("ooo")
        '''
        '''
        strategy_chart_soft = self.calculate_strategy_chart_soft(map_of_soft_scores, card_values, stat_chart)
        print("Strategy chart soft : ", strategy_chart_soft)
        total_soft_EV, sum_of_probas_soft = strategy_chart_soft.get_total_EV()
        print("Total soft EV : {}, sum of probas : {}".format("{0:.2f}".format(100*total_soft_EV), "{0:.2f}".format(100*sum_of_probas_soft)))
        input("ooo")
        '''
        strategy_chart_pair = self.calculate_strategy_chart_pair(map_of_pair_scores, card_values, stat_chart)
        print("Strategy chart pair : ", strategy_chart_pair)
        total_pair_EV, sum_of_probas_pair = strategy_chart_pair.get_total_EV()
        print("Total pair EV : {}, sum of probas : {}".format("{0:.2f}".format(100*total_pair_EV), "{0:.2f}".format(100*sum_of_probas_pair)))
        input("ooo")
        
        # Drawing the actual cards
        dealer_hand = Hand([self.shoe.deal()])
        self.dealer.set_hand(dealer_hand)

        player_hand = Hand([self.shoe.deal(), self.shoe.deal()])
        self.player.set_hands(player_hand, dealer_hand)
        # print "Dealer Hand: %s" % self.dealer.hand
        # print "Player Hand: %s\n" % self.player.hands[0]

##        dealer_stat_score = self.dealer.get_probabilities()
##        print("\nStatScore for the Dealer after drawing a '", dealer_stat_score.start_value, "':")
##        print(dealer_stat_score)
##
##        EVs = self.player.get_hand_EVs(player_hand, dealer_stat_score)
##        print ("Evs = ", EVs)
##
##        best_call = self.player.get_ideal_option(EVs)
##        print ("Best call : ", best_call)
##
##        input("Continue ?")
        
        #self.player.play(self.shoe)
        self.player.play(self.shoe, ideal_play = True, dealer = self.dealer)
        self.dealer.play(self.shoe)

        # print ""

        for hand in self.player.hands:
            win, bet = self.get_hand_winnings(hand)
            self.money += win
            self.bet += bet
            # print "Player Hand: %s %s (Value: %d, Busted: %r, BlackJack: %r, Splithand: %r, Soft: %r, Surrender: %r, Doubled: %r)" % (hand, status, hand.value, hand.busted(), hand.blackjack(), hand.splithand, hand.soft(), hand.surrender, hand.doubled)

        print("Dealer Hand: %s (%d)" % (self.dealer.hand, self.dealer.hand.value))

        #input("Continue ?")
        if self.shoe.reshuffle:
            self.shoe.reshuffle = False
            self.shoe.cards = self.shoe.init_cards()
            self.shoe.init_count()
            return True

        return False

    def get_money(self):
        return self.money

    def get_bet(self):
        return self.bet


if __name__ == "__main__":
    importer = StrategyImporter(sys.argv[1])
    HARD_STRATEGY, SOFT_STRATEGY, PAIR_STRATEGY = importer.import_player_strategy()

    moneys = []
    bets = []
    countings = []
    nb_hands = 0
    for g in range(GAMES):
        game = Game()
        reshuffled = False
        while(not(reshuffled)) :
            print("Game nb ", g)
            #print '%s GAME no. %d %s' % (20 * '#', i + 1, 20 * '#')
            reshuffled = game.play_round()
            nb_hands = nb_hands + 1

        moneys.append(game.get_money())
        bets.append(game.get_bet())
        countings += game.shoe.count_history

        print("WIN for Game no. %d: %s (%s bet)" % (g + 1, "{0:.2f}".format(game.get_money()), "{0:.2f}".format(game.get_bet())))

        sume = 0.0
        total_bet = 0.0
        for value in moneys:
        	sume += value
        for value in bets:
        	total_bet += value

        print()

        print(float(nb_hands)/GAMES, " hands per game, on average")
        print("{} hands, {} total bet".format(nb_hands, "{0:.2f}".format(total_bet)))
        print("Overall winnings: {} (edge = {} %)".format("{0:.2f}".format(sume), "{0:.3f}".format(100.0*sume/total_bet)))

        logger.info("Game {} winnings: {}. Overall winnings: {} (edge = {}%). {} hands. {} spreads ({}%)".format(g+1, "{0:.2f}".format(game.get_money()), "{0:.2f}".format(sume), "{0:.3f}".format(100.0*sume/total_bet), nb_hands, NB_SPREADS, 100*NB_SPREADS/nb_hands))

    """ #sigh
    moneys = sorted(moneys)
    fit = stats.norm.pdf(moneys, np.mean(moneys), np.std(moneys))  #this is a fitting indeed
    pl.plot(moneys,fit,'-o')
    pl.hist(moneys,normed=True) #use this to draw histogram of your data
    pl.show()                   #use may also need add this
    """
    
    plt.ylabel('count')
    plt.plot(countings, label='x')
    plt.legend()
    plt.show()
