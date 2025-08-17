import json
from cooperative_cuisine.base_agent.base_agent import BaseAgent, run_agent_from_args, parse_args
from cooperative_cuisine.base_agent.agent_task import Task
import asyncio

class MyAgent(BaseAgent):
    def __init__(self, bt_file: str, **kwargs):
        # Load behaviour tree from file
        with open(bt_file, "r") as f:
            self.behaviour_tree = json.load(f)
        self.bt_index = 0
        super().__init__(**kwargs)

    def _resolve_equipment_arg(self, arg, state):
        """
        Resolve an equipment argument with preference for unoccupied stoves when available.
        """
        if not isinstance(arg, str):
            return arg

        # Special handling for stoves - prefer unoccupied ones
        if arg.lower() in ["stove", "stoves"]:
            # First try to find an unoccupied stove
            for counter in state["counters"]:
                if counter.get("type") == "Stove" and not counter.get("occupied_by"):
                    return counter["id"]
            # If all stoves are occupied, return the first one found
            for counter in state["counters"]:
                if counter.get("type") == "Stove":
                    return counter["id"]
            raise ValueError("No stoves found in the environment")

        # Check all possible equipment categories in the state
        equipment_categories = [
            "counters",          # Regular counters
            "stoves",           # Stoves
            "pots",             # Pots
            "pans",             # Pans
            "deepfryers",       # Deep fryers
            "plates",           # Plates
            "cutting_boards",   # Cutting boards
            "sinks",            # Sinks
            "trashcans",        # Trash cans
            "serving_windows",  # Serving windows
            "conveyers"         # Conveyer belts
        ]

        # First check if it's an exact ID match
        for category in equipment_categories:
            if category in state:
                for item in state[category]:
                    if item["id"] == arg:
                        return arg

        # Then check for type matches
        for category in equipment_categories:
            if category in state:
                for item in state[category]:
                    if item["type"] == arg:
                        return item["id"]

        # Special case for cooking equipment that might be on cooking counters
        if "counters" in state:
            for counter in state["counters"]:
                if counter.get("occupied_by") and isinstance(counter["occupied_by"], dict):
                    if counter["occupied_by"].get("type") == arg:
                        return counter["id"]
                    if counter["occupied_by"].get("name") == arg:
                        return counter["id"]

        raise ValueError(f"No equipment found for type or id '{arg}'")

    async def manage_tasks(self, state):
        if self.bt_index >= len(self.behaviour_tree["steps"]):
            return  # Recipe finished

        if not self.current_task:
            step = self.behaviour_tree["steps"][self.bt_index]
            task_type = step["type"].upper()
            task_args = step.get("args", None)

            if task_args is not None:
                task_args = self._resolve_equipment_arg(task_args, state)

            self.set_current_task(Task(task_type=task_type, task_args=task_args))

    def finalize_current_task(self, status, reason):
        super().finalize_current_task(status, reason)
        if status.name == "SUCCESS":
            self.bt_index += 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bt-file", type=str, required=True, help="Path to behaviour tree JSON file")
    known_args, remaining_args = parser.parse_known_args()

    # Let BaseAgent parse its normal arguments
    base_args = parse_args(remaining_args)

    agent = MyAgent(
        bt_file=known_args.bt_file,
        player_id=base_args.player_id,
        step_time=base_args.step_time,
        recipe_graph=base_args.recipe_graph,
        diagonal_movements=not base_args.no_diagonal_movements,
        avoid_other_players=not base_args.ignore_other_players,
        vc_url=base_args.vc_url,
        vc_room=base_args.vc_room,
        smooth_paths=base_args.smooth_paths,
    )

    asyncio.run(agent.run_via_websocket(uri=base_args.uri, player_hash=base_args.player_hash))