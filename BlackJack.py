import sys
from random import shuffle

import numpy as np
import scipy.stats as stats
import pylab as pl
import matplotlib.pyplot as plt
import copy

from importer.StrategyImporter import StrategyImporter


GAMES = 200
# I'd rather consider a game is a full number of shoes played (the last hand might be shuffled in between though)
NB_SHOES_PER_GAME = 1
#ROUNDS_PER_GAME = 2000
SHOE_SIZE = 6
SHOE_PENETRATION = 0.25
BET_SPREAD = 20.0
BLACKJACK = "BJ"
BUSTED = "BU"

DECK_SIZE = 52.0
CARDS = {"Ace": 11, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10, "Jack": 10, "Queen": 10, "King": 10}
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
        [17, 18, 19, 20, 21, BJ, Busted] '''
    #TODO Differentiate 21 and BJ
    def get_probabilities(self) :
        print()
        print("*** START")
        print("COUNT = ", COUNT)
        print("nb_cards = ", nb_cards)
        start_value = int(self.hand.value)
        # We'll draw 5 cards no matter what and count how often we got 17, 18, 19, 20, 21, BJ, Busted

        print ("start_value = ", start_value)
        # The dealer will stop if his hand's value is any of stop_scores
        stat_score = StatScore(start_value, stop_scores=[17, 18, 19, 20, 21, BLACKJACK, BUSTED])
        print ("Stat_score (1 card) = ", stat_score)
        print()
        new_count = COUNT
        new_nb_cards = nb_cards

        for i in range(4) :
            print("Picking up a card from the deck (", i+1, ") ...")
            stat_card = StatCard(new_count, new_nb_cards)
            new_count, new_nb_cards = stat_card.get_new_count()
            print ("Stat_card = ", stat_card)
            print("Remaining proba = ", stat_score.remaining_proba)
            # "Nine" -> 9
            card_values = stat_card.get_card_values()
            print ("card_values = ", card_values)
            stat_score.draw_card(card_values)
            print ("Stat_score (", i+2, " cards) = ", stat_score)
            print("Remaining proba = ", stat_score.remaining_proba)
            print("new_count = ", new_count)
            print("new_nb_cards = ", new_nb_cards)
            print()

        print("** STOP")
        print()
        input("Continue ?")
"""
        stat_score_11 =
        stat_score_1 =
        print ("Stat_score_11 = ", stat_score_11)
        print ("Stat_score_1 = ", stat_score_1)


"""

class StatCard(object) :
    """
    Represents the probability of a card among ["Ace", "Two", ..., "King"].
    """
    # Creates a StatCard from the (ideal) count of the remaining cards.
    def __init__(self, count, nb_cards) :
        self.new_count = copy.deepcopy(count)
        self.new_nb_cards = nb_cards -1
        self.values = {}
        for c in count :
            self.values[c] = count[c]/float(nb_cards)
            # After picking a card, the likelihood of each value changes. new_count is updated to take that into account by
            # subtracting "portions" of cards, proportionally to the card's likeliness. The sum of the portions should be 1.0
            self.new_count[c] = self.new_count[c] - self.values[c]

    def __str__(self):
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

class StatScore(object) :
    """
    Represents the probability of a score among [2, 3, ..., 21, BlackJack, Busted].
    """
    def __init__(self, start_value, stop_scores=[21, BLACKJACK, BUSTED]):
        self.values = {}
        self.nb_cards_in_hand = 1
        self.stop_scores = stop_scores
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

    def __str__(self):
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
        final_remaining_proba = self.remaining_proba
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
            print("buff ratio = ", buff_ratio)
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
                    # There is a slime chance that we still have a soft ace in our hand, reducing the proba of busting
                    # and increasing the proba of reaching new_value - 10.
                    soft_ace_proba = old_soft_aces[score]
                    new_proba_busted = (card_values[v]*old_values[score])*self.remaining_proba*(1-soft_ace_proba)
                    new_proba_not_busted = (card_values[v]*old_values[score])*self.remaining_proba*(soft_ace_proba)

                    self.values[BUSTED] = new_proba_busted + self.values[BUSTED]

                    new_value = new_value - 10
                    if (new_value in self.stop_scores) :
                        final_remaining_proba = final_remaining_proba - new_proba_not_busted
                    self.values[new_value] = new_proba_not_busted + self.values[new_value]
                    # Important note : we turned a soft-11 ace into a hard-1 one. This increased the odds of reaching new_value, but it should also
                    # lower the odds of having a soft-11 ace on new_value (the small portion of hand population that we added has already a hard ace).
                    # TODO this effect is slightly complex to tackle (we need to calculate the probability of having exactly 2 aces, then exactly 3 ... exactly n)
                    # and is treated in the following way :
                    # we'll assume that the population that already got 1 soft ace turned will never have another that was already a soft 11 given by previous cards.
                    # Effect on the soft_ace_proba for new_value :
                    #self.soft_ace_proba[new_value] = self.soft_ace_proba[new_value] * (1.0 - population_ratio)
                    #TODO I probably did some awful mistake here :D Sleep some then fix some
                    #TODO I insist on this problem
                else :
                    # Updating the proba of having a soft ace only because of the previous cards
                    self.soft_ace_proba[new_value] = self.soft_ace_proba[new_value] + (card_values[v]*old_values[score]*old_soft_aces[score])*self.remaining_proba
                    if (new_value == 21 and self.nb_cards_in_hand == 2) :
                        new_value = BLACKJACK
                    new_proba = (card_values[v]*old_values[score])*self.remaining_proba
                    if (new_value in self.stop_scores) :
                        final_remaining_proba = final_remaining_proba - new_proba
                    self.values[new_value] = new_proba + self.values[new_value]

        # Updating the remaining proba. If it's 0, the player will never draw another card
        self.remaining_proba = final_remaining_proba


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
