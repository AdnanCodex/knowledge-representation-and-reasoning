% =====================================================================
%  Unification & Substitution
%  Run :  swipl -q -s unification.pl -g main -t halt
% =====================================================================

% ---- Our own unification algorithm ----
% Variables are written v(Name); a substitution is a list of Var-Term pairs.
% unify(X, Y, SubstIn, SubstOut)

is_var(v(_)).

unify(X, Y, S, S) :- X == Y, !.
unify(X, Y, S0, S) :- is_var(X), !, unify_var(X, Y, S0, S).
unify(X, Y, S0, S) :- is_var(Y), !, unify_var(Y, X, S0, S).
unify(X, Y, S0, S) :-
    compound(X), compound(Y),
    X =.. [F|As], Y =.. [F|Bs],
    length(As, N), length(Bs, N),
    unify_list(As, Bs, S0, S).

unify_list([], [], S, S).
unify_list([A|As], [B|Bs], S0, S) :-
    unify(A, B, S0, S1),
    unify_list(As, Bs, S1, S).

unify_var(V, X, S0, S) :- memberchk(V-T, S0), !, unify(T, X, S0, S).  % already bound
unify_var(V, X, _, _)  :- occurs(V, X), !, fail.                      % occurs-check
unify_var(V, X, S0, [V-X|S0]).

occurs(V, T) :- T == V, !.
occurs(V, T) :- compound(T), T =.. [_|As], member(A, As), occurs(V, A).

mgu(T1, T2) :-
    format('~w  ~~  ~w~n', [T1, T2]),
    (   unify(T1, T2, [], S0)
    ->  reverse(S0, S), format('   MGU: ~w~n', [S])
    ;   writeln('   MGU: none (unification fails)') ).

main :-
    writeln('=== Unification (own algorithm) ==='),
    mgu(loves(v('X'), ai),     loves(ali, v('Y'))),      % expected X/ali, Y/ai
    mgu(knows(v('X'), v('X')), knows(ali, v('Y'))),      % Task 1: X/ali, Y/ali
    mgu(loves(ali, ai),        loves(bob, ai)),          % Task 2: fails
    mgu(f(v('X'), g(v('Y'))),  f(a, g(b))),              % Task 3: X/a, Y/b
    mgu(v('X'),                f(v('X'))),               % occurs-check: fails
    writeln(''),
    writeln('=== Built-in unification (=) and occurs-check ==='),
    loves(X, ai) = loves(ali, Y),
    format('loves(X,ai) = loves(ali,Y):  X = ~w, Y = ~w~n', [X, Y]),
    (   unify_with_occurs_check(Z, f(Z))
    ->  writeln('Z = f(Z) unifies')
    ;   writeln('unify_with_occurs_check(Z, f(Z)) fails') ).
