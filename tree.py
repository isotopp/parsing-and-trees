#! /usr/bin/env python
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional, Generator

DEBUG = True


class Node:
    """ Eine Node hat einen Wert ``value`` und zwei optionale Nachfolger ``left`` und ``right``.

    Wir stellen drei Methoden bereit, die den Node-Baum durchlaufen:

    - ``preorder_walk()``: Durchläuft den Baum in Preorder-Reihenfolge.
    - ``inorder_walk()``: Durchläuft den Baum in Inorder-Reihenfolge.
    - ``postorder_walk()``: Durchläuft den Baum in Postorder-Reihenfolge.

    Außerdem gibt es eine Methode

    - ``postorder_apply(fn)``: Wendet die Methode `fn` auf den Baum in Postorder-Reihenfolge an.

    """
    def __init__(self, value: Any, left: Optional["Node"] = None, right: Optional["Node"] = None):
        self.value = value
        self.left = left
        self.right = right

    def __repr__(self):
        """ Return a string representation of the node. """
        left = "None"
        right = "None"
        if self.left is not None:
            left = self.left.value
        if self.right is not None:
            right = self.right.value

        # Was passiert, wenn wir stattdessen {self.left} und {self.right} einsetzen würden? → Rekursion (aber versteckt)
        return f"Node(value={self.value}, left={left}, right={right})"

    def preorder_walk(self):
        value = self.value
        print(f"{value}", end=' ')
        if self.left is not None:
            self.left.preorder_walk()
        if self.right is not None:
            self.right.preorder_walk()

    def inorder_walk(self):
        value = self.value

        if self.left is not None:
            self.left.inorder_walk()
        print(f"{value}", end=' ')
        if self.right is not None:
            self.right.inorder_walk()

    def postorder_walk(self):
        if self.left is not None:
            self.left.postorder_walk()
        if self.right is not None:
            self.right.postorder_walk()
        print(f"{self.value}", end=' ')

    def postorder_apply(self, fn):
        """ Wendet die Funktion `fn` in Postorder-Reihenfolge auf alle
            Nodes an, ausgehend von der aktuellen Node.
        """
        if self.left is not None:
            self.left.postorder_apply(fn)
        if self.right is not None:
            self.right.postorder_apply(fn)
        fn(self)


def ausrechnen(node):
    if DEBUG: print(f"  before {node=}")

    if node.value == '+':
        if node.left is None or node.right is None:
            raise RuntimeError(f"In {node}, found a none in {node.left=}, {node.right=}")

        node.value = node.left.value + node.right.value
        node.left = None
        node.right = None

    if node.value == '*':
        if node.left is None or node.right is None:
            raise RuntimeError(f"In {node}, found a none in {node.left=}, {node.right=}")

        node.value = node.left.value * node.right.value
        node.left = None
        node.right = None

    try:
        node.value = int(node.value)
    except ValueError:
        pass
    if DEBUG: print(f"  after  {node=}")


@dataclass(frozen=True, slots=True)
class Token:
    """ Ein ``Token`` hat immer einen ``type`` und einen ``value``.

     Der ``type`` kann `NUMBER` sein, der ``value`` ist dann ein ``int``.
     Der ``type`` kann ``OPERATOR`` sein, der ``value`` ist dann ein Einzeichenstring mit dem betreffenden Operator.

     Die Felder ``line`` und ``column`` sind optional und werden gebraucht, um Fehlermeldungen sinnvoll ausgeben zu können.
     """
    type: Any  # Enum: NUMBER, OPERATOR
    value: Any  # type == NUMBER -> value == int. type == OPERATOR -> value = str mit len(value)==1
    line: int = field(default=None, compare=False)
    column: int = field(default=None, compare=False)


class Lexer:
    """ Verbesserter Lexer.

     Der Lexer hat eine Generator-Methode ``tokenize()``, die jeweils das nächste Token zurück gibt.
     """
    def __init__(self, the_input: str):
        self.input = the_input
        self.len = len(self.input)

        self.offset = 0
        self.line = 0
        self.column = 0

    def tokenize(self) -> Generator[Token, None, None]:
        NUMBER = re.compile(r"(-?\d+)", re.ASCII)
        OPERATOR = ['+', '*']

        while self.offset < self.len:
            c = self.input[self.offset]

            if c == '\n':
                self.line += 1
                self.offset += 1
                self.column = 0
                yield Token(type='EOL', value='\n', line=self.line, column=self.column)
            elif c.isspace():
                self.offset += 1
                self.column += 1
            elif m := re.match(NUMBER, self.input[self.offset:]):
                self.offset += len(m[0])
                self.column += len(m[0])
                yield Token(type='NUMBER', value=int(m[0]), line=self.line, column=self.column)
            elif c in OPERATOR:
                self.offset += 1
                self.column += 1
                yield Token(type='OPERATOR', value=c, line=self.line, column=self.column)
            else:
                self.offset += 1
                self.column += 1
                yield Token(type='char', value=c, line=self.line, column=self.column)

        self.offset += 1
        self.column += 1
        yield Token(type='EOF', value='\n', line=self.line, column=self.column)


class Parser:
    """ Ein recursive descent Parser für die folgende Grammatik:
    ::

      term := factor ( '+' factor )*
      factor := primary ( '*' primary )*
      primary := NUMBER

    Die einzelnen Regeln werden in Methoden des Namens implementiert: factor in ``factor()`` und so weiter.
    Die Produktionsregeln geben jeweils den Typ ``Node`` zurück, die Spitze des Parsebaumes bisher.

    """
    def __init__(self, lexer: Lexer):
        self.tokens = [t for t in lexer.tokenize()]
        self.pos = 0
        self.len = len(self.tokens)

    def peek(self, msg) -> Optional[Token]:
        if self.pos >= self.len:
            if DEBUG: print(f"Peek {msg}: None {self.pos}, {self.len}")
            return None

        t = self.tokens[self.pos]
        if DEBUG: print(f"Peek {msg}: {t}, {self.pos}, {self.len}")
        return t

    def consume(self) -> Optional[Token]:
        if self.pos >= self.len:
            if DEBUG: print(f"Consume: None {self.pos}, {self.len}")
            return None

        t = self.tokens[self.pos]
        if DEBUG: print(f"Consume: {t} {self.pos}, {self.len}")
        self.pos += 1
        return t

    def error(self, msg: str) -> None:
        t = self.tokens[self.pos]

        print(f'Error {msg} at {t.line}:{t.column}', file=sys.stderr)
        sys.exit(1)

    def term(self) -> Node:
        """term := factor ( '+' factor )*

        Ein Term ist ein Factor, optional gefolgt einer Gruppe "Operator +" und weiterer Faktor.
        """
        TERMOPS = [Token(type='OPERATOR', value='+'), ]  # Kann um '-' erweitert werden.
        if DEBUG: print("Enter Term")
        left = self.factor()

        while self.peek('+') in TERMOPS:
            t = self.consume()
            right = self.factor()
            left = Node(value=t.value, left=left, right=right)

        if DEBUG: print(f"Exit  Term: {left}")
        return left

    def factor(self) -> Node:
        """factor := primary ( '*' primary )*

         Ein Faktor ist ein Primary, optional gefolgt einer Gruppe "Operator *" und einem weiteren Primary."""
        FACTOROPS = [Token(type='OPERATOR', value='*')]  # Kann um '/' erweitert werden.
        if DEBUG: print("Enter Factor")
        left = self.primary()

        while self.peek('*') in FACTOROPS:
            t = self.consume()
            right = self.primary()
            left = Node(value=t.value, left=left, right=right)

        if DEBUG: print(f"Exit  Factor: {left}")
        return left

    def primary(self) -> Node:
        """primary := NUMBER

        Ein Primary ist eine NUMBER."""
        if DEBUG: print("Enter Primary")
        t = self.consume()
        if t.type == 'NUMBER':
            n = Node(value=t.value)
            if DEBUG: print(f"Exit  Primary: {n}")
            return n
        # elif self.peek() == Token(type='OPERATOR', value='('):
        #   _ = self.consume()
        #   n = self.term()
        #   closing = self.consume()
        #   if closing != Token(type='OPERATOR', value=')'):
        #     self.error("Expected closing parenthesis.")
        else:
            self.error(f'Unexpected token {t.type}')

    def parse(self) -> Node:
        self.tree = self.term()
        return self.tree



if __name__ == "__main__":
    expr = "2 * 3 + 4 * 5"
    l = Lexer(expr)
    print(f"{l.input=}")

    parser = Parser(lexer=l)
    tree = parser.parse()

    tree.postorder_walk()
    print()

    tree.postorder_apply(ausrechnen)
    print(f"{tree=}")
