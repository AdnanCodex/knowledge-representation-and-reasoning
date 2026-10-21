% =====================================================================
%  Resolution Refutation Theorem Proving
%  Run :  swipl -q -s resolution_refutation.pl -g main -t halt
%  Clauses are lists of literals; negation is written ~p
% =====================================================================

:- op(200, fy, ~).

negate(~A, A) :- !.
negate(A, ~A).

% resolve(Ci, Cj, R): R is a resolvent of clauses Ci and Cj
resolve(Ci, Cj, R) :-
    member(L, Ci), negate(L, NL), member(NL, Cj),
    delete(Ci, L, Ci1), delete(Cj, NL, Cj1),
    append(Ci1, Cj1, R0), sort(R0, R).

% saturate(Clauses, Round): resolve all pairs until [] is found
% (success) or no new clause can be derived (failure).
saturate(Cs, _) :-
    member(A, Cs), member(B, Cs), A \== B, resolve(A, B, []), !,
    format('  ~w + ~w  =>  [] (empty clause)~n', [A, B]).
saturate(Cs, N) :-
    findall(R, (member(A, Cs), member(B, Cs), A \== B, resolve(A, B, R)), Rs0),
    sort(Rs0, Rs), subtract(Rs, Cs, New),
    New \== [],
    forall(member(C, New), format('  round ~w: derived ~w~n', [N, C])),
    append(Cs, New, Cs2), N1 is N + 1,
    saturate(Cs2, N1).

% entails(KB, Query): proof by refutation
entails(KB, Query) :-
    negate(Query, NQ),
    maplist(sort, KB, KB1),
    format('  negated goal added: ~w~n', [[NQ]]),
    (   saturate([[NQ]|KB1], 1)
    ->  format('  KB entails ~w: True~n', [Query])
    ;   format('  KB entails ~w: False (no contradiction)~n', [Query]) ).

main :-
    writeln('=== Resolution Refutation ==='),
    writeln('--- Example: {p->q, p} |= q'),
    entails([[~p, q], [p]], q),
    writeln('--- Task 1: {p v q, ~p} |= q'),
    entails([[p, q], [~p]], q),
    writeln('--- Task 2: {p, p->q, q->r} |= r'),
    entails([[p], [~p, q], [~q, r]], r),
    writeln('--- Task 3: {p v q} |= p  (no proof)'),
    entails([[p, q]], p).
