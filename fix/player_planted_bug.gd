extends CharacterBody2D
## Double jump with a PLANTED bug (from the brief): the extra jump is only granted when the player jumps from
## the floor. Walk off a ledge without jumping, press jump in mid-air, and nothing happens.

const SPEED := 220.0
const JUMP_VELOCITY := -420.0
const AIR_JUMP_VELOCITY := -360.0

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
var air_jumps_left := 0


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y += gravity * delta
	if Input.is_action_just_pressed("jump"):
		if is_on_floor():
			velocity.y = JUMP_VELOCITY
			air_jumps_left = 1
		elif air_jumps_left > 0:
			velocity.y = AIR_JUMP_VELOCITY
			air_jumps_left -= 1
	var direction := Input.get_axis("move_left", "move_right")
	velocity.x = direction * SPEED
	move_and_slide()
