"""Count completed optimizer calls without replacing optimizer methods."""

WORK_VERSION = "optimizer-step-calls-v1"


class OptimizerWork:
    def __init__(self, model, algorithm):
        if algorithm not in ("ppo", "sac"):
            raise ValueError("Unknown optimizer-work algorithm")
        self.model, self.algorithm = model, algorithm
        self.handles = []
        self.entered = False
        if algorithm == "ppo":
            self.optimizers = {"policy": model.policy.optimizer}
        else:
            self.optimizers = {"actor": model.actor.optimizer, "critic": model.critic.optimizer}
            if model.ent_coef_optimizer is not None:
                self.optimizers["entropy_temperature"] = model.ent_coef_optimizer
        if len({id(optimizer) for optimizer in self.optimizers.values()}) != len(self.optimizers):
            raise ValueError("Optimizer names alias the same optimizer")
        self.counts = {name: 0 for name in self.optimizers}

    def _hook(self, name):
        def completed(optimizer, args, kwargs):
            self.counts[name] += 1
        return completed

    def __enter__(self):
        if self.entered:
            raise RuntimeError("Optimizer-work instrumentation cannot be reused")
        self.entered = True
        try:
            for name, optimizer in self.optimizers.items():
                self.handles.append(optimizer.register_step_post_hook(self._hook(name)))
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for handle in self.handles:
            handle.remove()
        self.handles.clear()

    def summary(self):
        return {
            "version": WORK_VERSION,
            "algorithm": self.algorithm,
            "optimizer_step_calls": dict(self.counts),
            "total_optimizer_step_calls": sum(self.counts.values()),
            "sb3_internal_update_counter": int(self.model._n_updates),
            "units": "Completed optimizer.step calls, not epochs, samples, FLOPs, or wall time",
            "counter_scope": "This learn invocation only; failed optimizer calls are not counted",
        }
