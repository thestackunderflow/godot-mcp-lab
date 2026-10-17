extends CharacterBody2D
## Reference double jump (the lab's expected answer, NOT the agent's work): one extra jump while airborne,
## reset whenever the player stands on the floor, so it also works after walking off a ledge.

const SPEED := 220.0
const JUMP_VELOCITY := -420.0
const AIR_JUMP_VELOCITY := -360.0   # the second jump is a little weaker

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
var air_jumps_left := 0


func _physics_process(delta: float) -> void:
	if is_on_floor():
		air_jumps_left = 1
	else:
		velocity.y += gravity * delta
	if Input.is_action_just_pressed("jump"):
		if is_on_floor():
			velocity.y = JUMP_VELOCITY
		elif air_jumps_left > 0:
			velocity.y = AIR_JUMP_VELOCITY
			air_jumps_left -= 1
	var direction := Input.get_axis("move_left", "move_right")
	velocity.x = direction * SPEED
	move_and_slide()
