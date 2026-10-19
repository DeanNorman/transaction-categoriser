"""Rules decide the known cases before any model is asked (decisions 0002 and 0004).

The table is ordered: specific merchants first, then money movement, then plain words per category. The first
rule whose pattern matches the normalised description wins. Each rule carries the category, how sure we are, and
the reason a person would give. Patterns are matched against the output of `normalise()`: lower case, no punctuation.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from .categories import Category
from .normalise import normalise

MERCHANT = Decimal("0.98")  # a named merchant whose business is one category
STRONG = Decimal("0.90")  # a plain word that almost always means one category
LIKELY = Decimal("0.70")  # defensible, but a reviewer could argue
UNSURE = Decimal("0.50")  # kept away from the model on purpose, flagged for a person


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str
    category: str
    confidence: Decimal
    reason: str

    def matches(self, normalised):
        return re.search(self.pattern, normalised) is not None


@dataclass(frozen=True)
class RuleMatch:
    rule: str
    category: str
    confidence: Decimal
    reason: str


RULES = [
    # Named merchants: one business, one category.
    Rule("albert-heijn", r"\balbert heijn\b|\bah\b", Category.GROCERIES, MERCHANT, "Albert Heijn is a supermarket"),
    Rule("supermarkets", r"\bjumbo\b|\blidl\b|\baldi\b|\bplus\b|\bdirk\b|\bcoop\b|\bspar\b|\bpicnic\b", Category.GROCERIES, MERCHANT, "a supermarket"),
    Rule("ns", r"\bns\b|\bnederlandse spoorwegen\b", Category.TRANSPORTATION, MERCHANT, "NS is the Dutch railway"),
    Rule("transport-brands", r"\bgvb\b|\bret\b|\bhtm\b|\bov chipkaart\b|\bovpay\b|\bshell\b|\bbp\b|\btinq\b|\bq8\b", Category.TRANSPORTATION, MERCHANT, "public transport or fuel"),
    Rule("eneco", r"\beneco\b|\bvattenfall\b|\bessent\b|\bgreenchoice\b|\bbudget energie\b", Category.UTILITIES, MERCHANT, "an energy supplier"),
    Rule("ziggo", r"\bziggo\b|\bkpn\b|\bodido\b|\bt mobile\b|\bvodafone\b|\btele2\b", Category.UTILITIES, MERCHANT, "internet, TV or phone provider"),
    Rule("water", r"\bvitens\b|\bwaternet\b|\bevides\b|\bdunea\b|\bpwn\b", Category.UTILITIES, MERCHANT, "a water company"),
    Rule("streaming", r"\bnetflix\b|\bspotify\b|\bdisney\b|\bvideoland\b|\bhbo\b|\bprime video\b", Category.ENTERTAINMENT, MERCHANT, "a streaming subscription"),
    Rule("cinema", r"\bpathe\b|\bkinepolis\b|\bvue\b|\bbioscoop\b|\bcinema\b|\bconcert\b|\bticketmaster\b", Category.ENTERTAINMENT, STRONG, "a cinema or event"),
    Rule("online-shops", r"\bbol com\b|\bbol\b|\bzalando\b|\bcoolblue\b|\bamazon\b|\bhema\b|\bikea\b|\bmediamarkt\b|\baction\b|\bwehkamp\b", Category.SHOPPING, MERCHANT, "a shop"),
    Rule("food-delivery", r"\bthuisbezorgd\b|\buber eats\b|\bdeliveroo\b|\bdominos\b|\bmcdonalds\b|\bstarbucks\b", Category.DINING_OUT, MERCHANT, "food delivery or a restaurant chain"),
    Rule("pharmacy", r"\bapotheek\b|\bpharmacy\b|\betos\b|\bkruidvat\b|\bda\b", Category.HEALTHCARE, MERCHANT, "a pharmacy or drugstore"),
    Rule("health-insurers", r"\bzilveren kruis\b|\bcz\b|\bvgz\b|\bmenzis\b|\bdsw\b|\bzorgverzekering\b", Category.HEALTHCARE, MERCHANT, "health insurance"),
    Rule("universities", r"\buva\b|\bvu\b|\btu delft\b|\berasmus\b|\bduo\b|\budemy\b|\bcoursera\b", Category.EDUCATION, MERCHANT, "a university, student finance or a course provider"),

    # Housing before the bank rules: a mortgage is housing even when a bank's name is in the description.
    Rule("rent", r"\brent\b|\bhuur\b", Category.HOUSING, Decimal("0.95"), "rent is housing"),
    Rule("mortgage", r"\bmortgage\b|\bhypotheek\b|\bvve\b", Category.HOUSING, Decimal("0.95"), "a mortgage or owners' association charge"),
    Rule("municipal-tax", r"\bmunicipal tax\b|\bgemeente\b|\bgemeentelijke\b|\bozb\b|\bwaterschap\b", Category.HOUSING, LIKELY, "municipal property and household taxes (decision 0004)"),

    # Money movement: never spending, so never sent to the model (decision 0004).
    Rule("salary", r"\bsalary\b|\bsalaris\b|\bloon\b|\bwages\b", Category.MISCELLANEOUS, Decimal("0.95"), "income, not spending"),
    Rule("tax-refund", r"\btax refund\b|\bbelastingdienst\b|\bteruggave\b", Category.MISCELLANEOUS, STRONG, "tax, money in or out of the tax office, not spending"),
    Rule("card-repayment", r"\bcredit card\b|\bcreditcard\b", Category.MISCELLANEOUS, Decimal("0.95"), "repayment of a card: the spending was categorised when it happened"),
    Rule("cash", r"\batm\b|\bgeldmaat\b|\bcash withdrawal\b|\bgeldautomaat\b", Category.MISCELLANEOUS, STRONG, "cash withdrawal, purpose unknown"),
    Rule("own-transfer", r"\btransfer to\b|\bbunq\b|\brevolut\b|\bknab\b|\bsavings\b|\bspaarrekening\b", Category.MISCELLANEOUS, STRONG, "transfer to another account"),
    Rule("payment-to-bank", r"\bpayment to (ing|rabobank|abn amro|abn|sns|asn|triodos)\b", Category.MISCELLANEOUS, UNSURE, "a payment to a bank: transfer, loan or mortgage instalment; a person should check"),
    Rule("payment-rail", r"\bideal\b|\bpaypal\b|\btikkie\b|\bklarna\b", Category.MISCELLANEOUS, UNSURE, "a payment rail with no merchant named; a person could look up the counterparty"),

    # Plain words per category, for merchants not in the table.
    Rule("groceries-words", r"\bsupermarkt\b|\bsupermarket\b|\bgroceries\b|\bgrocery\b", Category.GROCERIES, STRONG, "groceries"),
    Rule("dining-words", r"\brestaurant\b|\bcafe\b|\bbar\b|\bbistro\b|\bpizzeria\b|\bsushi\b|\blunch\b|\bdinner\b|\bsnackbar\b|\beetcafe\b", Category.DINING_OUT, STRONG, "eating out"),
    Rule("utility-words", r"\benergy\b|\benergie\b|\belectricity\b|\bgas\b|\bwater\b|\binternet\b|\bmobile\b|\btelecom\b", Category.UTILITIES, STRONG, "a utility"),
    Rule("transport-words", r"\btrain\b|\btrein\b|\bbus\b|\btram\b|\bmetro\b|\btaxi\b|\buber\b|\bparking\b|\bparkeren\b|\bfuel\b|\btank\b|\bcar lease\b|\blease\b|\bbenzine\b", Category.TRANSPORTATION, STRONG, "getting around"),
    Rule("health-words", r"\bhuisarts\b|\bdoctor\b|\bdentist\b|\btandarts\b|\bhospital\b|\bziekenhuis\b|\bfysio\b|\bclinic\b", Category.HEALTHCARE, STRONG, "health care"),
    Rule("education-words", r"\buniversity\b|\buniversiteit\b|\bcollegegeld\b|\btuition\b|\bschool\b|\bcourse\b|\bcursus\b|\btextbook\b", Category.EDUCATION, STRONG, "education"),
    Rule("entertainment-words", r"\bsubscription\b|\bgame\b|\bgames\b|\bmuseum\b|\btheater\b|\btheatre\b|\bfestival\b", Category.ENTERTAINMENT, LIKELY, "entertainment"),
]


def match(description):
    """The first rule that matches the normalised description, or None when the model should be asked."""
    normalised = normalise(description)
    for rule in RULES:
        if rule.matches(normalised):
            return RuleMatch(rule.name, rule.category, rule.confidence, rule.reason)
    return None
