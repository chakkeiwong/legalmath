
:- op(800, fx, user:(<-)).
:- use_module(library(http/json)).
:- use_module(library(readutil)).
:- initialization(main, main).
main :-
 current_prolog_flag(argv, [Module, Input, Output]),
 use_module(Module), read_file_to_string(Input, Text, []), atom_string(Atom, Text),
 le_input:clear_errors,
 catch((le_input:text_to_logic(Atom, Translation) -> Success=true ; Success=false, Translation=[]),
       Exception, (Success=false, Translation=[], term_string(Exception, ExceptionText))),
 findall(S, (le_input:error_notice(A,B,C,D), term_string(error_notice(A,B,C,D), S)), Errors),
 copy_term(Translation, Stable), numbervars(Stable, 0, _),
 term_string(Stable, Terms, [quoted(true), numbervars(true)]),
 findall(C, (member(if(_, H, B), Translation), copy_term((H:-B), Clause),
             numbervars(Clause, 0, _), term_string(Clause, C, [quoted(true), numbervars(true)])), Clauses),
 (var(ExceptionText) -> ExceptionText="" ; true),
 open(Output, write, Stream),
 json_write_dict(Stream, _{parsed:Success, errors:Errors, exception:ExceptionText, translation:Terms, clauses:Clauses}),
 close(Stream).
