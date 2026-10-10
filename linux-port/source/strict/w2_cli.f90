! Synchronous entry adapter for the approved CE-QUAL-W2 4.5.5 source.
! Compile only for CLI_ONLY. Input/control-file restart semantics stay in solver.
PROGRAM W2
  USE IFPORT, ONLY: CHDIR
  USE, INTRINSIC :: ISO_FORTRAN_ENV, ONLY: ERROR_UNIT
  USE GLOBAL, ONLY: CDATE, CCTIME
  USE MSCLIB, ONLY: RESTART_PUSHED, STOP_PUSHED
  IMPLICIT NONE
  INTEGER :: STATUS, ARGUMENT_LENGTH, ARGUMENT_STATUS
  CHARACTER(255) :: MODEL_DIRECTORY
  INTERFACE
    INTEGER FUNCTION CE_QUAL_W2 ()
    END FUNCTION CE_QUAL_W2
  END INTERFACE

  ! Match RUN / OUTPUT_DIALOG's fresh-launch state before CreateThread.
  CALL DATE_AND_TIME (CDATE,CCTIME)
  RESTART_PUSHED = .FALSE.
  STOP_PUSHED = .FALSE.
  ! Reject truncation and failed directory changes before any solver file I/O.
  ! The original solver handled this argument; the CLI branch now does it here.
  CALL GET_COMMAND_ARGUMENT(1, MODEL_DIRECTORY, ARGUMENT_LENGTH, ARGUMENT_STATUS)
  IF (COMMAND_ARGUMENT_COUNT() > 0) THEN
    IF (ARGUMENT_STATUS /= 0 .OR. ARGUMENT_LENGTH > LEN(MODEL_DIRECTORY)) THEN
      WRITE (ERROR_UNIT,'(A)') 'Cannot read model-directory argument (maximum 255 characters).'
      STOP 2
    END IF
  END IF
  IF (ARGUMENT_LENGTH /= 0) THEN
    STATUS = CHDIR(TRIM(MODEL_DIRECTORY))
    IF (STATUS /= 0) THEN
      WRITE (ERROR_UNIT,'(A,I0,2A)') 'Cannot enter model directory (status ', STATUS, '): ', TRIM(MODEL_DIRECTORY)
      STOP 2
    END IF
  END IF
  STATUS = CE_QUAL_W2 ()
  IF (STATUS /= 0) STOP 1
END PROGRAM W2
