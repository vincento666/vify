from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType


class UnsupportedTaskCommand(ValueError):
    pass


class CustomerAssistantActionPolicy:
    def validate(self, commands: list[TaskCommand]) -> None:
        for command in commands:
            if not isinstance(command, TaskCommand):
                raise UnsupportedTaskCommand(f"Unsupported command object: {type(command).__name__}")
            if command.type not in set(TaskCommandType):
                raise UnsupportedTaskCommand(f"Unsupported command type: {command.type}")
            if command.type in {
                TaskCommandType.ADD_TASK,
                TaskCommandType.RETAIN_TASK,
                TaskCommandType.CANCEL_TASK,
                TaskCommandType.SUSPEND_TASK,
                TaskCommandType.RESUME_TASK,
                TaskCommandType.CALL_WORKER,
            } and not command.task_key:
                raise UnsupportedTaskCommand(f"Command requires task_key: {command.type.value}")
            if command.type == TaskCommandType.ADD_TASK:
                missing = [
                    field_name
                    for field_name in ("task_type", "business_key", "worker_type", "worker_ref")
                    if not getattr(command, field_name)
                ]
                if missing:
                    raise UnsupportedTaskCommand(f"ADD_TASK missing fields: {', '.join(missing)}")
