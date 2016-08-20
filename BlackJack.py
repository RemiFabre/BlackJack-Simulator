import sys
from random import shuffle

import numpy as np
import scipy.stats as stats
import pylab as pl
import matplotlib.pyplot as plt

from importer.StrategyImporter import StrategyImporter


GAMES = 200
# I'd rather consider a game is a full number of shoes played (the last hand might be shuffled in between though)
NB_SHOES_PER_GAME = 1
#ROUNDS_PER_GAME = 2000
SHOE_SIZE = 6
SHOE_PENETRATION = 0.25
BET_SPREAD = 20.0

DECK_SIZE = 52.0
CARDS = {"Ace": 11, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10, "Jack": 10, "Queen": 10, "King": 10}
BASIC_OMEGA_II = {"Ace": 0, "Two": 1, "Three": 1, "Four": 2, "Five": 2, "Six": 2, "Seven": 1, "Eight": 0, "Nine": -1, "Ten": -2, "Jack": -2, "Queen": -2, "King": -2}
COUNT = {"Ace": SHOE_SIZE*4, "Two": SHOE_SIZE*4, "Three": SHOE_SIZE*4, "Four": SHOE_SIZE*4, "Five": SHOE_SIZE*4, "Six": SHOE_SIZE*4, "Seven": SHOE_SIZE*4, "Eight": SHOE_SIZE*4, "Nine": SHOE_SIZE*4, "Ten": SHOE_SIZE*4, "Jack": SHOE_SIZE*4, "Queen": SHOE_SIZE*4, "King": SHOE_SIZE*4}
nb_cards = DECK_SIZE*SHOE_SIZE

HARD_STRATEGY = {}
SOFT_STRATEGY = {}
PAIR_STRATEGY = {}


def get_statistical_card_from_count(count, nb_cards) :
    for c in count :
        count[c] = count[c]/float(nb_cards)
    return count

class Card(object):
    """
    Represents a playing card with name and value.
    """
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
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

    def __str__(self):
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
        global COUNT
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

    def __str__(self):
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

    def play(self, shoe):
        for hand in self.hands:
            # print "Playing Hand: %s" % hand
            self.play_hand(hand, shoe)

    def play_hand(self, hand, shoe):
        if hand.length() < 2:
            if hand.cards[0].name == "Ace":
                hand.cards[0].value = 11
            self.hit(hand, shoe)

        while not hand.busted() and not hand.blackjack():
            if hand.soft():
                flag = SOFT_STRATEGY[hand.value][self.dealer_hand.cards[0].name]
            elif hand.splitable():
                flag = PAIR_STRATEGY[hand.value][self.dealer_hand.cards[0].name]
            else:
                flag = HARD_STRATEGY[hand.value][self.dealer_hand.cards[0].name]

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
                self.split(hand, shoe)

            if flag == 'S':
                break

    def hit(self, hand, shoe):
        c = shoe.deal()
        hand.add_card(c)
        # print "Hitted: %s" % c

    def split(self, hand, shoe):
        self.hands.append(hand.split())
        # print "Splitted %s" % hand
        self.play_hand(hand, shoe)


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

    ''' Returns an array of 7 numbers representing the probability that the final score of the dealer is
        [17, 18, 19, 20, 21, Busted] '''
    #TODO Differentiate 21 and BJ
    def get_probabilities(self) :
        start_value = self.hand.value
        # We'll draw 5 cards no matter what and count how often we got 17, 18, 19, 20, 21, Busted
        tree = Tree([Leave(start_value, 1.0)])
        stat_card = get_statistical_card_from_count(COUNT, nb_cards)
        print("stat_card : ", stat_card)
        print("1 card : \n", tree)
        proba_of_done = tree.add_a_statistical_card_dealer(stat_card, 1.0)
        print("proba_of_done : ", proba_of_done)
        print("2 card : \n", tree)
        proba_of_done = tree.add_a_statistical_card_dealer(stat_card, 1.0 - proba_of_done)
        print("proba_of_done : ", proba_of_done)
        print("3 card : \n", tree)
        proba_of_done = tree.add_a_statistical_card_dealer(stat_card, 1.0 - proba_of_done)
        print("proba_of_done : ", proba_of_done)
        print("4 card : \n", tree)
        proba_of_done = tree.add_a_statistical_card_dealer(stat_card, 1.0 - proba_of_done)
        print("proba_of_done : ", proba_of_done)
        print("5 card : \n", tree)
        proba_of_done = tree.add_a_statistical_card_dealer(stat_card, 1.0 - proba_of_done)


class Leave(object):
    """
    Possible value, with a probability
    """
    def __init__(self, value, proba):
        self.over = False
        self.value = value
        self.proba = proba

    def __str__(self):
        s = "[" + str(self.value) + ", " + "{0:.2f}".format(100*self.proba) + "]"
        if (self.over) :
            s += "o"
        return s

#TODO A tree has a fixed number of leaves starting from line 2 (about 21 + BJ + busted). A leave has a status "finished"
class Tree(object):
    """
    A tree that opens with a statistical card and changes as a new
    statistical card is added. In this context, a statistical card is a list of leaves.
    e.g : [2 : 0.05, 3 : 0.1, ..., 22 : 0.1]
    Any value above 21 will be truncated to 22, which means 'Busted'.
    """
    def __init__(self, start=[]):
        self.tree = start

    def __str__(self):
        s = ""
        for l in self.tree:
            s += str(l) + "  "
        s += "\n"
        return s

    def leaves_have_value(self, leaves, value) :
        index = -1
        for l in leaves :
            index = index + 1
            if (l.value == value) :
                return index
        return -1

        #TODO Handle Aces !
        #TODO The statistical card should change as the carts are drawn ...
    def add_a_statistical_card_dealer(self, stat_card, proba_of_not_done):
        # New set of leaves in the tree
        leaves = []
        # Probability of being done with this card
        done_proba = 0
        for leave in self.tree :
            for v in stat_card :
                if (leave.over) :
                    new_value = leave.value
                    proba = leave.proba
                else :
                    new_value = int(CARDS[v] + leave.value)
                    proba = leave.proba*stat_card[v]
                if (new_value > 21) :
                    # All busted values are 22
                    new_value = 22
                if (new_value >= 17) :
                    leave.over = True
                    done_proba = done_proba + proba
                index = self.leaves_have_value(leaves, new_value)
                if (index == -1) :
                    # The list of leaves doesn't have this value
                    leaves.append(Leave(new_value, proba))
                else :
                    leaves[index].proba = leaves[index].proba + proba_of_not_done*proba
        leaves = sorted(leaves, key=lambda leave: leave.value)
        self.tree = leaves
        return done_proba

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
            win += 1.5
        elif status == "SURRENDER":
            win += -0.5
        if hand.doubled:
            win *= 2
            bet *= 2

        win *= self.stake

        return win, bet

    # Returns true if a reshuffle took place during the round
    def play_round(self):
        if self.shoe.truecount() > 6:
            self.stake = BET_SPREAD
        else:
            self.stake = 1.0

        player_hand = Hand([self.shoe.deal(), self.shoe.deal()])
        dealer_hand = Hand([self.shoe.deal()])
        self.player.set_hands(player_hand, dealer_hand)
        self.dealer.set_hand(dealer_hand)
        # print "Dealer Hand: %s" % self.dealer.hand
        # print "Player Hand: %s\n" % self.player.hands[0]
        self.dealer.get_probabilities()

        self.player.play(self.shoe)
        self.dealer.play(self.shoe)

        # print ""

        for hand in self.player.hands:
            win, bet = self.get_hand_winnings(hand)
            self.money += win
            self.bet += bet
            # print "Player Hand: %s %s (Value: %d, Busted: %r, BlackJack: %r, Splithand: %r, Soft: %r, Surrender: %r, Doubled: %r)" % (hand, status, hand.value, hand.busted(), hand.blackjack(), hand.splithand, hand.soft(), hand.surrender, hand.doubled)

        # print "Dealer Hand: %s (%d)" % (self.dealer.hand, self.dealer.hand.value)

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
            # print '%s GAME no. %d %s' % (20 * '#', i + 1, 20 * '#')
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

    moneys = sorted(moneys)
    fit = stats.norm.pdf(moneys, np.mean(moneys), np.std(moneys))  #this is a fitting indeed
    pl.plot(moneys,fit,'-o')
    pl.hist(moneys,normed=True) #use this to draw histogram of your data
    pl.show()                   #use may also need add this

    plt.ylabel('count')
    plt.plot(countings, label='x')
    plt.legend()
    plt.show()
