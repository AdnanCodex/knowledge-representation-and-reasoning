% =====================================================================
%  First-Order Logic - Formalizing a Domain
%  Run :  swipl -q -s first_order_logic.pl -g main -t halt
%  Or interactively:  swipl first_order_logic.pl   then   ?- mortal(X).
% =====================================================================

:- discontiguous student/1.

% ---- English -> First Order Logic ----
% 1. All humans are mortal.      forall x ( human(x) -> mortal(x) )
% 2. Socrates is a human.        human(socrates)
% 3. Some student loves AI.      exists x ( student(x) AND loves(x, ai) )

% ---- Same knowledge in Prolog ----
human(socrates).
human(plato).
student(ali).
loves(ali, ai).
mortal(X) :- human(X).            % forall x: human(x) -> mortal(x)

% ---- Task 1: Every dog has an owner ----
% forall x ( dog(x) -> exists y owns(y, x) )
dog(rex).
dog(bella).
owns(ali, rex).
owns(sara, bella).
has_owner(D)   :- dog(D), owns(_, D).
owner_of(D, O) :- dog(D), owns(O, D).

% ---- Task 2: University domain ----
student(sara).
student(bilal).
course(krr).
course(ai).
enrolled(ali, krr).
enrolled(sara, krr).
enrolled(sara, ai).
classmates(A, B) :- enrolled(A, C), enrolled(B, C), A \= B.
idle(S)          :- student(S), \+ enrolled(S, _).

% ---- Task 3: No fish is a mammal ----
% forall x ( fish(x) -> not mammal(x) )   (negation as failure)
fish(salmon).
fish(shark).
mammal(dolphin).
mammal(whale).
violation(X)  :- fish(X), mammal(X).
consistent    :- \+ violation(_).
not_mammal(X) :- fish(X), \+ mammal(X).

% ---- Helpers ----
show(G) :- \+ \+ ( numbervars(G,0,_),
                   format('?- ~W.~n', [G,[numbervars(true),quoted(true)]]) ).
check(G) :- show(G), ( call(G) -> writeln('   true') ; writeln('   false') ).
all(T,G) :- show(G), findall(T,G,L), format('   ~w~n', [L]).

main :-
    writeln('=== First-Order Logic in Prolog ==='),
    check(mortal(socrates)),
    check(loves(ali, ai)),
    all(X, mortal(X)),
    all(S, (student(S), loves(S, ai))),
    writeln('--- Task 1: dogs ---'),
    check(has_owner(rex)),
    all(D, has_owner(D)),
    all(D-O, owner_of(D, O)),
    writeln('--- Task 2: university ---'),
    all(S1, enrolled(S1, krr)),
    all(C, enrolled(sara, C)),
    all(A-B, classmates(A, B)),
    all(S2, idle(S2)),
    writeln('--- Task 3: no fish is a mammal ---'),
    check(mammal(salmon)),
    all(F, not_mammal(F)),
    check(consistent).
