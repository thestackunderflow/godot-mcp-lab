extends CharacterBody2D
## The player: walk left/right, jump once from the ground. (No double jump yet: that's the agent's task.)

const SPEED := 220.0
const JUMP_VELOCITY := -420.0

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y += gravity * delta
	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY
	var direction := Input.get_axis("move_left", "move_right")
	velocity.x = direction * SPEED
	move_and_slide()
