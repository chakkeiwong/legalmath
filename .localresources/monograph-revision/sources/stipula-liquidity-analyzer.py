from classes.data.abstract_computation import AbsComputation
from classes.data.visitor_entry import FunctionVisitorEntry, EventVisitorEntry
from classes.data.liquidity_expression import LiqExpr, LiqConst

class LiquidityAnalyzer:
    def __init__(self, function_frequency):
        # maximum number of times a function can appear in the same abstract computation (k-canonical)
        self.K = function_frequency

        self.Q0 : str = ''  # initial state
        self.global_assets: list[str] = list()

        self.functions: set[FunctionVisitorEntry] = set()
        self.events: set[EventVisitorEntry] = set()
        self.abs_computations: set[AbsComputation] = set()

        self.states: set[str] = set()
        self.reachable_states: set[str] = set()

        self.Tqk : dict[str, set[AbsComputation]] = dict()
        self.Qq : dict[str, set[FunctionVisitorEntry | EventVisitorEntry]] = dict()     # unused (not in the thesis)

        self.has_events: bool = False
        self.has_guards: bool = False

    # region compute results
    def compute_verbose_results(self) -> None:
        print("VERBOSE INFORMATION\n\tFunction Liquidity Types:")
        for entry in (self.functions | self.events):
            entry_env = entry.get_env()
            print(f"\t\t{entry}")
            print(f"\t\t\tLIQUIDITY TYPE:")
            print(f"\t\t\t\t{entry_env['start']} -> {entry_env['end']}")
            print(f"\t\t\tASSET TYPES:")
            print(f"\t\t\t\t{entry.get_asset_types()}")
            if isinstance(entry, FunctionVisitorEntry):
                print(f"\t\t\tEVENTS LIST:")
                print(f"\t\t\t\t{entry.events_list}")

        print("\tAbstract Computations:")
        for abs_computation in self.abs_computations:
            abs_comp_env = abs_computation.get_env()
            print(f"\t\t{abs_computation}")
            print(f"\t\t\tLIQUIDITY TYPE:")
            print(f"\t\t\t\t{abs_comp_env['start']} -> {abs_comp_env['end']}")
            print(f"\t\t\tASSET TYPES:")
            print(f"\t\t\t\t{abs_computation.get_asset_types()}")
            print(f"\t\t\tARE ALL ASSET TYPES SINGLETON:")
            print(f"\t\t\t\t{abs_computation.get_are_all_types_singleton()}")
        print("================================================================================================")

    def compute_results(self) -> tuple[dict, tuple[bool, str], bool, bool, bool]:
        self.compute_states()
        # Computes abs_comps before local_liq, so abs_comps are always already available in verbose
        self.compute_abs_computations()

        are_all_types_singleton = all(
            abs_computation.get_are_all_types_singleton()
            for abs_computation in self.abs_computations
        )
        function_local_liquidity = self.compute_function_local_liquidity()
        if not function_local_liquidity[0]:
            k_separate_result = {k: function_local_liquidity for k in self.global_assets}
            return (k_separate_result, function_local_liquidity,
                    self.has_events, self.has_guards, not are_all_types_singleton)

        self.compute_reachable_states()
        self.compute_tqk()

        result_liquidity = self.costly_algorithm_complete()
        if result_liquidity[0]:
            result_k_separate = {k: (True, "") for k in self.global_assets}
        else:
            result_k_separate = self.costly_algorithm_k_separate()

        return (result_k_separate, result_liquidity,
                self.has_events, self.has_guards, not are_all_types_singleton)
    # endregion compute results

    # region getter, setter
    def set_q0(self, state_id):
        self.Q0 = state_id

    def add_visitor_function(self, visitor_entry: FunctionVisitorEntry, has_guard: bool = False):
        self.functions.add(visitor_entry)
        self.has_guards = self.has_guards | has_guard

    def add_visitor_event(self, visitor_entry: EventVisitorEntry):
        self.events.add(visitor_entry)
        self.has_events = True

    def add_global_asset(self, asset):
        self.global_assets.append(asset.text)

    def get_global_asset(self) -> list[str]:
         return self.global_assets
    # endregion setter

    def compute_function_local_liquidity(self) -> tuple[bool, str]:
        """
            Compute local liquidity for each function.
            Checks if all the local assets are emptied to respond to Definition 1 - Constraint 1

            :return: True if all the functions are liquid, otherwise False
        """
        for entry in self.functions:
            par = entry.compute_local_liquidity()
            if par:
                return False, f"{entry} is NOT local liquid for {par}"
        return True, ""

    def compute_states(self):
        """
        Computes all the states
        """
        self.states = set()
        for entry in self.events | self.functions:
            # fill states set
            self.states.add(entry.start_state)
            self.states.add(entry.end_state)

    def compute_abs_computations(self) -> None:
        """
        Compute abstract computations starting from Q0
        """
        for function in self.functions:
            if function.start_state == self.Q0:
                # create an abs_computation formed only by the function if function starts in Q0
                abs_computation = AbsComputation()
                abs_computation.insert_configuration(function)
                for event in function.events_list:
                    abs_computation.add_available_event(event)
                self.abs_computations.add(abs_computation)

        is_change = True
        while is_change:
            is_change = False
            computations_to_add : set[AbsComputation] = set()
            for abs_computation in self.abs_computations:
                for function in self.functions:
                    if function.start_state == abs_computation.get_last_state():
                        new_abs_computation = abs_computation.copy_abs_computation()
                        if abs_computation.count(function) < self.K:
                            new_abs_computation.insert_configuration(function)
                            for event in function.events_list:
                                new_abs_computation.add_available_event(event)
                        computations_to_add.add(new_abs_computation)
                for event in abs_computation.get_available_events():
                    if event.start_state == abs_computation.get_last_state():
                        new_abs_computation = abs_computation.copy_abs_computation()
                        new_abs_computation.remove_available_event(event)
                        new_abs_computation.insert_configuration(event)
                        computations_to_add.add(new_abs_computation)

            is_change = is_change or bool(computations_to_add.difference(self.abs_computations))
            self.abs_computations.update(computations_to_add)

    def compute_reachable_states(self) -> None:
        """
        Computes the set of states reachable from the initial state Q0 and saves them in self.reachable_states.

        The method performs a depth-first search (DFS) over the automaton
        transitions, treating states as nodes and transitions as directed edges.
        Only reachability is considered; transition labels are ignored.
        """
        visited = { self.Q0 }
        stack = [ self.Q0 ]

        while stack:
            q = stack.pop()
            for entry in (self.functions | self.events):
                if entry.start_state == q:
                    q_next = entry.end_state
                    if q_next not in visited:
                        visited.add(q_next)
                        stack.append(q_next)

        self.reachable_states = visited

    def compute_tqk(self) -> None:
        for state in self.states:
            self.Tqk[state] = set()
        for abs_computation in self.abs_computations:
            for configuration in abs_computation:
                self.Tqk[configuration.start_state].add(abs_computation.copy_abs_computation(configuration.start_state))

    # region efficient algorithm (unused)
    def compute_qq(self) -> None:
        for state in self.states:
            self.Qq[state] = set()
        for entry in (self.functions | self.events):
            self.Qq[entry.start_state].add(entry)
        is_change = True
        while is_change:
            is_change = False
            for entry in (self.functions | self.events):
                prev_len = len(self.Qq[entry.start_state])
                self.Qq[entry.start_state] |= self.Qq[entry.end_state]
                self.Qq[entry.start_state].add(entry)
                if len(self.Qq[entry.start_state]) > prev_len:
                    is_change = True

    def efficient_algorithm_k_separate(self) -> bool:
        # step 1
        self.compute_qq()
        z : set[tuple[str, str]] = set()

        found_missing_tuple = True
        while found_missing_tuple:
            found_missing_tuple = False
            # step 2
            for entry in self.Qq[self.Q0]:
                entry_env = entry.get_env()
                for k in self.global_assets:
                    # step 2.a, 2.b
                    if (entry_env['start'][k] != entry_env['end'][k] and
                        entry_env['end'][k] != LiqExpr(LiqConst.EMPTY) and
                        (entry.end_state, k) not in z
                    ):
                        found_missing_tuple = True
                        is_missing_tuple_added = False
                        # step 2.2
                        for next_entry in self.Qq[entry.end_state]:
                            next_entry_env = next_entry.get_env()
                            if next_entry_env['end'][k] == LiqExpr(LiqConst.EMPTY):
                                is_missing_tuple_added = True
                                z.add((entry.end_state, k))
                                break
                        if not is_missing_tuple_added:
                            print(f"\t\t\t\tEFFICIENT K-SEPARATE: {entry}, {k}")
                            return False
        # step 2.1
        return True

    def efficient_algorithm_complete(self) -> bool:
        # step 1
        z : set[str] = set()

        h = tuple()
        for k in self.global_assets:
            h += (k,)

        found_missing_tuple = True
        while found_missing_tuple:
            found_missing_tuple = False
            # step 2
            for entry in self.Qq[self.Q0]:
                entry_env = entry.get_env()

                h_not_zero = any(
                    entry_env['end'][k] != LiqExpr(LiqConst.EMPTY)
                    for k in self.global_assets
                )
                if h_not_zero and entry_env['start']!=entry_env['end'] and entry.end_state not in z:
                    found_missing_tuple = True
                    is_missing_tuple_added = False
                    # step 2.2
                    for next_entry in self.Qq[entry.end_state]:
                        next_entry_env = next_entry.get_env()
                        all_zero = all(
                            next_entry_env['end'][k] == LiqExpr(LiqConst.EMPTY)
                            for k in self.global_assets
                        )
                        if all_zero:
                            is_missing_tuple_added = True
                            z.add(entry.end_state)
                            break
                    if not is_missing_tuple_added:
                        print(f"\t\t\t\tEFFICIENT COMPLETE: {entry}")
                        return False
        # step 2.1
        return True
    # endregion efficient algorithm (unused)

    # region costly algorithm
    def costly_algorithm_k_separate(self) -> dict:
        result = dict()
        for k in self.global_assets:
            result[k] = self.costly_algorithm_k_separate_asset(k)
        return result

    def costly_algorithm_k_separate_asset(self, k: str) -> tuple[bool, str]:
        z : set[tuple[str,str]] = set(tuple())
        is_missing_state_found = True
        while is_missing_state_found:
            is_missing_state_found = False
            for state in self.reachable_states:
                for abs_computation in self.Tqk[state]:
                    abs_computation_env = abs_computation.get_env()
                    if (abs_computation_env['end'][k] != LiqExpr(LiqConst.EMPTY) and
                        abs_computation_env['start'][k] != abs_computation_env['end'][k] and
                        (abs_computation.get_last_state(),k) not in z
                    ):
                        is_missing_state_found = True
                        is_missing_state_added = False
                        for abs_computation_p in self.Tqk[abs_computation.get_last_state()]:
                            abs_computation_p_env = abs_computation_p.get_env()
                            if abs_computation_p_env['end'][k] == LiqExpr(LiqConst.EMPTY):
                                z.add((abs_computation.get_last_state(),k))
                                is_missing_state_added = True
                                break
                        if not is_missing_state_added:
                            return False, f"comp: {abs_computation}"
        return True, ""


    def costly_algorithm_complete(self) -> tuple[bool, str]:
        z : set[tuple[str,frozenset[str]]] = set()
        for state in self.reachable_states:
            for abs_computation in self.Tqk[state]:
                abs_computation_env = abs_computation.get_env()
                kbar = set()
                for k in self.global_assets:
                    if (abs_computation_env['end'][k] != LiqExpr(LiqConst.EMPTY)
                        and abs_computation_env['start'][k] != abs_computation_env['end'][k]):
                        kbar.add(k)
                if kbar and (abs_computation.get_last_state(), frozenset(kbar)) not in z:
                    is_found = False
                    for abs_computation_p in self.Tqk[abs_computation.get_last_state()]:
                        is_abs_comp_valid = True
                        for k in kbar:
                            if abs_computation_p.get_env()['end'][k] != LiqExpr(LiqConst.EMPTY):
                                is_abs_comp_valid = False
                                break
                        if is_abs_comp_valid:
                            for h in set(self.global_assets) - kbar:
                                if (abs_computation_p.get_env()['end'][h] != LiqExpr(LiqConst.EMPTY) and
                                    abs_computation_p.get_env()['start'][h] != abs_computation_p.get_env()['end'][h]):
                                    is_abs_comp_valid = False
                                    break
                        if is_abs_comp_valid:
                            z.add((abs_computation.get_last_state(), frozenset(kbar)))
                            is_found = True
                            break
                    if not is_found:
                        return False, f"{kbar} in comp: {abs_computation}"
        return True, ""
    # endregion costly algorithm